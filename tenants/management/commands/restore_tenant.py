import io
import logging
from argparse import ArgumentParser, RawTextHelpFormatter
from pathlib import Path
from typing import Any, Dict, Optional, Set

import boto3
from boto3_type_annotations.s3 import Client
from django.contrib.sites.models import Site
from django.core.management import call_command, CommandError
from django.core.management.commands.loaddata import Command as BaseLoadDataCommand
from django.db import connection

from tenants.management.argparse import (
    LOCATION_TYPE,
    S3Options,
    location_type,
    remove_actions,
)

from ..gzip_dump_manager import TenantDump
from ..media_manager import MediaManager
from . import backup_tenant

logger = logging.getLogger(__name__)


class Command(BaseLoadDataCommand):
    help = "Restore the database contents of a tenant's JSON dump."
    missing_args_message = None
    epilog = backup_tenant.Command.epilog

    DEFAULT_EXCLUDE_LIST: Set[str] = {"tenants"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._manager: Optional[TenantDump] = None
        self.super_cmd_options: Optional[Dict[str, Any]] = None

    def add_arguments(self, parser: ArgumentParser, add_location_arg=True):
        super().add_arguments(parser)
        remove_actions(parser, "args")

        parser.epilog = self.epilog
        parser.formatter_class = RawTextHelpFormatter
        if add_location_arg:
            parser.add_argument(
                "location",
                help="The local path or URL of the file to restore from. See --help.",
                type=location_type,
            )

    def _get_dump_from_s3(self, *, opts: S3Options) -> None:
        s3_client: Client = boto3.client("s3")
        obj_data = s3_client.get_object(**opts)
        content_type = obj_data.get("ContentType")
        body_stream = obj_data["Body"]

        if content_type != "application/x-gzip":
            raise CommandError(f"Unsupported backup format: {content_type}")

        try:
            with io.BytesIO() as fp_out:
                fp_out.writelines(body_stream)
                fp_out.seek(0)
                self._manager.decompress_all(fileobj=fp_out)
        finally:
            body_stream.close()

    def _get_dump_from_local(self, *, path: Path) -> None:
        self._manager.decompress_all(archive_path=path)

    def prepare_for_restore(self, location: LOCATION_TYPE, **base_options):
        self._manager = TenantDump()
        self.super_cmd_options = base_options

        self._manager.start()

        try:
            if isinstance(location, S3Options):
                logger.info(f"Retrieving archive from {location}...")
                self._get_dump_from_s3(opts=location)
            elif isinstance(location, Path):
                self._get_dump_from_local(path=location)
            else:
                raise NotImplementedError(type(location), location)
        except Exception as exc:
            self._manager.stop()
            raise exc

    def _run_django_load_data(self, *dump_paths, **options):
        return super().handle(*dump_paths, **options)

    def _run_media_restore(self):
        MediaManager(self._manager.media_dir).upload()
        call_command("create_thumbnails")

    def run_restore(self):
        if not connection.tenant:
            raise CommandError("No tenant selected.")

        options = self.super_cmd_options
        dump_path = str(self._manager.schema_path)
        domain = connection.tenant.domain_url

        try:
            logger.info("Restoring the data...")
            self._run_django_load_data(dump_path, **options)
            self._run_media_restore()

            site: Site = Site.objects.get()
            if site.domain != domain:
                logger.info("Updating outdated site domain...")
                site.domain = domain
                site.save(update_fields=["domain"])
        finally:
            self._manager.stop()

    def handle(self, *_, **options):
        self.prepare_for_restore(**options)
        self.run_restore()
