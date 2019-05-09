from django.conf import settings
from django.db import connection

from tenants.management.argparse import location_type

from ...models import Tenant
from . import restore_tenant


class Command(restore_tenant.Command):
    help = "Create new tenant and dedicated database schema"

    def add_arguments(self, parser):
        parser.add_argument(
            "domain_url", type=str, metavar="DOMAIN_URL", help="Tenant domain url"
        )
        parser.add_argument(
            "-s",
            "--schema",
            type=str,
            metavar="SCHEMA",
            help="Tenant database schema name",
        )
        parser.add_argument(
            "-r",
            "--restore",
            dest="location",
            metavar="LOCATION",
            help="The local path or URL of the file to restore from. See --help.",
            type=location_type,
        )
        super().add_arguments(parser, add_location_arg=False)
        parser.set_defaults(bucket_name=settings.DEFAULT_BACKUP_BUCKET_NAME)

    def handle(self, *_, domain_url: str, schema: str, **options):
        domain_url = domain_url.lower()
        default_schema_name = domain_url.split(".")[0]
        schema_name = schema or default_schema_name

        restore_from_location = options.get("location")

        if restore_from_location:
            self.prepare_for_restore(**options)

        tenant = Tenant(domain_url=domain_url, schema_name=schema_name)
        tenant.save()

        if restore_from_location:
            connection.set_tenant(tenant)
            try:
                self.run_restore()
            except Exception as exc:
                tenant.delete()
                raise exc
