import io
import logging
import subprocess
import urllib.parse
from argparse import ArgumentParser, RawTextHelpFormatter
from pathlib import Path
from typing import Any, Dict, Optional, Set

import boto3
from boto3_type_annotations.s3 import Client
from django.contrib.sites.models import Site
from django.core.management import call_command, CommandError, BaseCommand
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
from ..sql_dump_manager import SqlManager
from ...utils import preserve_tenant, assure_connection_initialized

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Restore the database contents of a tenant's SQL dump."
    missing_args_message = None
    epilog = backup_tenant.Command.epilog

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._manager: Optional[TenantDump] = None
        self.super_cmd_options: Optional[Dict[str, Any]] = None

    def add_arguments(self, parser: ArgumentParser, add_location_arg=True):
        super().add_arguments(parser)
        remove_actions(parser, "args")

        parser.epilog = self.epilog
        parser.formatter_class = RawTextHelpFormatter

        parser.add_argument(
            "--skip_media",
            action="store_true",
            help="Skip restoring media files. Ignored if --restore not provided",
        )
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

            backup_skip_media = self._manager.metadata.get("skip_media", False)
            if base_options["skip_media"] is False and backup_skip_media is True:
                raise CommandError(
                    "Selected backup does not include media files. Add --skip_media flag to restore this backup"
                )
        except Exception as exc:
            self._manager.stop()
            raise exc

    def _run_load_data(self):
        metadata = self._manager.metadata
        sql_dump_filename = self._manager.schema_path
        source_schema = metadata["schema_name"]
        target_schema = connection.tenant.schema_name

        logger.info("Loading backup...")
        sql_dump = SqlManager(sql_dump_filename)

        logger.info(
            f"Replacing schema name in backup: {source_schema} -> {target_schema}"
        )
        sql_dump.update(source_schema, target_schema)

        self._drop_schema(target_schema)
        self._execute_sql_dump(sql_dump_filename)

    @staticmethod
    def _drop_schema(schema_name):
        cursor = connection.cursor()
        cursor.execute(f"DROP SCHEMA IF EXISTS {schema_name} CASCADE")

    @preserve_tenant
    @assure_connection_initialized
    def _execute_sql_dump(self, sql_dump_filename):
        logger.info("Executing SQL script with a backup...")
        db_info = connection.connection.info
        constr = f"postgres://{db_info.user}:{urllib.parse.quote(db_info.password)}@{db_info.host}/{db_info.dbname}"
        subprocess.check_call(["psql", "-f", sql_dump_filename, constr])
        logger.info("Done!")
        logger.info("Running migrations...")
        call_command("migrate_schemas", schema_name=connection.tenant.schema_name)

    def _run_media_restore(self):
        MediaManager(self._manager.media_dir).upload()
        call_command("create_thumbnails")

    @staticmethod
    def _update_tenant_site_domain():
        domain = connection.tenant.domain_url
        site: Site = Site.objects.get()
        if site.domain != domain:
            logger.info("Updating outdated site domain...")
            site.domain = domain
            site.save(update_fields=["domain"])

    def run_restore(self, skip_media=False):
        if not connection.tenant:
            raise CommandError("No tenant selected.")

        try:
            logger.info("Restoring the data...")
            self._run_load_data()
            if not skip_media:
                self._run_media_restore()

            self._update_tenant_site_domain()
        finally:
            self._manager.stop()

    def handle(self, *_, **options):
        self.prepare_for_restore(**options)
        self.run_restore(skip_media=options["skip_media"])
