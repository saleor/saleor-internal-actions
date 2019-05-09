from typing import Optional

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import connection

from tenants.management.argparse import location_type

from ...models import Tenant
from .backup_tenant import Command as BackupTenantCommand


class Command(BaseCommand):
    help = "Delete tenant and drop dedicated database schema"

    def add_arguments(self, parser):
        parser.add_argument(
            "domain_url", type=str, metavar="DOMAIN_URL", help="Tenant domain url"
        )
        parser.add_argument(
            "-b",
            "--backup",
            dest="location",
            metavar="LOCATION",
            help="The local path or URL of the file to restore from. See --help.",
            type=location_type,
        )

        BackupTenantCommand().add_arguments(parser, add_location_arg=False)

    @staticmethod
    def _create_backup(tenant, location, **options):
        connection.set_tenant(tenant, include_public=False)
        call_command("backup_tenant", location, **options)
        connection.set_schema_to_public()

    def handle(self, *args, domain_url: str, **options):
        domain_url = domain_url.lower()
        backup_location = options.get("location")

        try:
            tenant = Tenant.objects.get(domain_url=domain_url)
        except Tenant.DoesNotExist:
            raise CommandError(
                'Tenant for domain: "{}" does not exist'.format(domain_url)
            )

        if backup_location:
            self._create_backup(tenant, **options)

        tenant.delete()
