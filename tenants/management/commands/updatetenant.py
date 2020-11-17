from django.contrib.sites.models import Site
from django.core.management.base import BaseCommand
from django.db import connection

from tenants.models import Tenant


def update_domain(new_domain):
    tenant = Tenant.objects.get(id=connection.tenant.id)
    base_tenant_domain = tenant.domain_url
    tenant.domain_url = new_domain
    tenant.save(update_fields=["domain_url"])

    site = Site.objects.get()
    if site.domain == base_tenant_domain:
        site.domain = new_domain
        site.save(update_fields=["domain"])


def update_allowed_client_origins(allowed_client_origins):
    tenant = Tenant.objects.get(id=connection.tenant.id)
    tenant.allowed_client_origins = allowed_client_origins
    tenant.save(update_fields=["allowed_client_origins"])


class Command(BaseCommand):
    help = "Updates the tenant"

    def add_arguments(self, parser):
        parser.add_argument(
            "--new-domain", type=str, dest="new_domain", help="New tenant domain url"
        )
        parser.add_argument(
            "--allowed-client-origins",
            dest="allowed_client_origins",
            help="List of allowed client origins",
            nargs="*",
        )

    def handle(self, *args, new_domain: str, allowed_client_origins: list, **options):
        if new_domain is not None:
            update_domain(new_domain)
        if allowed_client_origins is not None:
            update_allowed_client_origins(allowed_client_origins)
