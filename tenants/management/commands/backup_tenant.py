import logging
import subprocess
import urllib.parse
from argparse import ArgumentParser, RawTextHelpFormatter
from pathlib import Path

import boto3
from boto3_type_annotations.s3 import Client
from django.core.management import BaseCommand, CommandError
from django.db import connection

from tenants.management.argparse import (
    LOCATION_TYPE,
    S3Options,
    location_type,
    remove_actions,
)
from tenants.management.gzip_dump_manager import TenantDump
from tenants.management.media_manager import MediaManager
from tenants.utils import assure_connection_initialized

logger = logging.getLogger(__name__)
BACKUP_VERSION = 1


class Command(BaseCommand):
    help = "Dump the contents of a tenant's database to SQL format"
    epilog = """\
LOCATION
\t-\tA local absolute or relative path.
\t-\tA S3 RFC 1738 URL: s3://[BUCKET_NAME]/S3_FILE_KEY
\t\tIf no BUCKET_NAME was supplied, it will fallback to DEFAULT_BACKUP_BUCKET_NAME
\t\tif any.

EXAMPLES OF VALID S3 LOCATIONS
\t- s3://my_bucket.example.com/backup_20190921.tar.gz
\t- s3:///backup_20190921

ENVIRONMENT VARIABLES:
\t-\tDEFAULT_BACKUP_BUCKET_NAME: the default bucket name."""

    def add_arguments(self, parser: ArgumentParser, add_location_arg=True):
        super().add_arguments(parser)
        remove_actions(parser, "args")

        parser.epilog = self.epilog
        parser.formatter_class = RawTextHelpFormatter
        if add_location_arg:
            parser.add_argument(
                "location",
                help="The local path or URL to save the tar file backup onto. See --help.",
                type=location_type,
            )
        parser.add_argument(
            "--skip_media", action="store_true", help="Do not include media in backup"
        )

    @staticmethod
    def _upload(from_path: Path, *, opts: S3Options):
        s3_client: Client = boto3.client("s3")
        with open(from_path, mode="rb") as fp:
            s3_client.put_object(
                Body=fp,
                ContentType="application/x-gzip",
                Tagging=f"BackupVersion={BACKUP_VERSION}",
                **opts,
            )

    @staticmethod
    def _run_media_backup(media_dir):
        logger.info("Downloading media...")
        MediaManager(media_dir).download()
        logger.info("Done!")

    def handle(self, location: LOCATION_TYPE, skip_media=False, **options):
        if not connection.tenant:
            raise CommandError("No tenant selected.")

        save_path = location if isinstance(location, Path) else None

        with TenantDump() as backup:
            prev_include_public = connection.include_public_schema
            connection.set_tenant(connection.tenant, include_public=False)
            schema_name = connection.tenant.schema_name

            logger.info(
                "Creating backup for tenant %s into %s",
                connection.tenant.domain_url,
                location,
            )

            try:
                run_dump_data(schema_name=schema_name, target=backup.schema_path)
                if not skip_media:
                    self._run_media_backup(backup.media_dir)
                backup.add_metadata(
                    schema_name=schema_name,
                    domain=connection.tenant.domain_url,
                    skip_media=skip_media,
                )
            finally:
                connection.set_tenant(connection.tenant, prev_include_public)

            logger.info("Archiving the backup...")
            backup.archive_all(archive_path=save_path)

            if save_path is not None:
                return

            if isinstance(location, S3Options):
                logger.info("Uploading archive to %s...", location)
                self._upload(backup.get_archive_path(), opts=location)


@assure_connection_initialized
def run_dump_data(schema_name, target):
    logger.info("Dumping database...")
    db_info = connection.connection.info
    constr = f"postgres://{db_info.user}:{urllib.parse.quote(db_info.password)}@{db_info.host}/{db_info.dbname}"
    subprocess.check_call(
        ["pg_dump", "-n", schema_name, "-f", target, "--quote-all-identifiers", constr,]
    )
    logger.info("Done!")
