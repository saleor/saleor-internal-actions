from django.contrib.sites.models import Site
from django.core.management.base import BaseCommand, CommandError
from tenant_schemas.utils import tenant_context

from ...models import Tenant


class Command(BaseCommand):
    help = "Updates the tenant domain"

    def add_arguments(self, parser):
        parser.add_argument(
            "current_domain", type=str, help="Current tenant domain url"
        )
        parser.add_argument("new_domain", type=str, help="New tenant domain url")

    def handle(self, *args, current_domain: str, new_domain: str, **options):
        try:
            tenant = Tenant.objects.get(domain_url=current_domain)
        except Tenant.DoesNotExist:
            raise CommandError(f"No tenant with domain {current_domain}")
        base_tenant_domain = tenant.domain_url
        tenant.domain_url = new_domain
        tenant.save()

        with tenant_context(tenant):
            site = Site.objects.get()
            if site.domain == base_tenant_domain:
                site.domain = new_domain
                site.save()
