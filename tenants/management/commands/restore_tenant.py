import io
import logging
import json
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

    def _replace_dump_schema(self, dump: str, source_schema: str, target_schema: str):
        logger.info(f"Replacing schema name in backup: {source_schema} -> {target_schema}")
        dump = f'DROP SCHEMA IF EXISTS "{target_schema}" CASCADE;\n' + dump

        replaceable = [
            'CREATE SCHEMA "{schema_name}"',
            'ALTER SCHEMA "{schema_name}"',
            'CREATE TABLE "{schema_name}".',
            'OWNED BY "{schema_name}".',
            'SET DEFAULT "nextval"(\'"{schema_name}".',
            'COPY "{schema_name}".',
            'pg_catalog.setval(\'"{schema_name}".',
            'ON "{schema_name}".',
            'CREATE SEQUENCE "{schema_name}".',
            'ALTER SEQUENCE "{schema_name}".',
            'ALTER TABLE "{schema_name}".',
            'ALTER TABLE ONLY "{schema_name}".',
            'REFERENCES "{schema_name}".',
        ]
        for r in replaceable:
            dump = dump.replace(
                r.format(schema_name=source_schema), r.format(schema_name=target_schema)
            )
        return dump

    def _run_load_data(self, dump_path: str, metadata_path: str, target_schema: str):
        logger.info("Loading backup...")
        with open(metadata_path) as meta_fh:
            meta = json.load(meta_fh)
            source_schema = meta["schema_name"]
        with open(dump_path) as dump_fh:
            dump = dump_fh.read()
        dump = self._replace_dump_schema(dump, source_schema, target_schema)
        with open(dump_path, "wt") as dump_fh:
            dump_fh.write(dump)

        logger.info("Executing SQL script with a backup...")
        db_info = connection.connection.info
        constr = f"postgres://{db_info.user}:{urllib.parse.quote(db_info.password)}@{db_info.host}/{db_info.dbname}"
        subprocess.check_call(["psql", "-f", dump_path, constr])
        logger.info("Done!")
        logger.info("Running migrations...")
        call_command("migrate_schemas", schema_name=target_schema)

    def _run_media_restore(self):
        MediaManager(self._manager.media_dir).upload()
        call_command("create_thumbnails")

    def run_restore(self):
        if not connection.tenant:
            raise CommandError("No tenant selected.")

        dump_path = str(self._manager.schema_path)
        metadata_path = str(self._manager.metadata_path)
        domain = connection.tenant.domain_url
        target_schema = connection.tenant.schema_name

        try:
            logger.info("Restoring the data...")
            self._run_load_data(dump_path, metadata_path, target_schema)
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
