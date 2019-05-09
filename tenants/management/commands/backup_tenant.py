import logging
from argparse import ArgumentParser, RawTextHelpFormatter
from pathlib import Path
from typing import Set

import boto3
from boto3_type_annotations.s3 import Client
from django.core.management import CommandError
from django.core.management.commands.dumpdata import Command as BaseDumpDataCommand
from django.db import connection

from tenants.management.argparse import (
    LOCATION_TYPE,
    S3Options,
    location_type,
    remove_actions,
)
from tenants.management.gzip_dump_manager import TenantDump

logger = logging.getLogger(__name__)


class Command(BaseDumpDataCommand):
    help = (
        "Dump the contents of a tenant's database to JSON format "
        "(using each model's default manager unless --all is specified)."
    )
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

    DEFAULT_EXCLUDE_LIST: Set[str] = {"tenants"}

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
            "-l",
            "--compression-level",
            default=6,
            type=int,
            help=(
                "Specifies the compression level for gzip (default). "
                "The default compression level is 6, "
                "giving the best ratio of compression ratio vs CPU time"
            ),
        )
        parser.add_argument(
            "--restrict",
            action="append",
            dest="app_labels",
            metavar="app_label[.ModelName]",
            help=(
                "Restricts dumped data to the specified app_label "
                "or app_label.ModelName."
            ),
            default=[],
        )
        parser.set_defaults(indent=2)

    @staticmethod
    def _upload(from_path: Path, *, opts: S3Options):
        s3_client: Client = boto3.client("s3")
        with open(from_path, mode="rb") as fp:
            s3_client.put_object(Body=fp, ContentType="application/x-gzip", **opts)

    def _run_django_dump_data(self, *app_labels, **options):
        return super().handle(*app_labels, **options)

    def handle(self, app_labels, location: LOCATION_TYPE, compression_level, **options):
        if not connection.tenant:
            raise CommandError("No tenant selected.")

        options["exclude"] = set(options["exclude"]) | self.DEFAULT_EXCLUDE_LIST
        save_path = location if isinstance(location, Path) else None

        with TenantDump() as archive:
            prev_include_public = connection.include_public_schema
            connection.set_tenant(connection.tenant, include_public=False)

            options["output"] = archive.schema_path

            try:
                self._run_django_dump_data(*app_labels, **options)
            finally:
                connection.set_tenant(connection.tenant, prev_include_public)

            archive.compress_all(archive_path=save_path, level=compression_level)

            if save_path is not None:
                return

            if isinstance(location, S3Options):
                logger.info(f"Uploading archive to {location}...")
                self._upload(archive.get_archive_path(), opts=location)
