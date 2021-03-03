from django.contrib.sites.models import Site
from django.core.management.base import BaseCommand
from django.db import connection, transaction

from tenants.management.billing_plan_manager import BillingPlanManagement, T_LIMITS
from tenants.models import Tenant


def update_domain(tenant: Tenant, new_domain):
    """Updates tenant's domain_url and site domain configuration"""
    base_tenant_domain = tenant.domain_url
    tenant.domain_url = new_domain

    site = Site.objects.get()
    if site.domain == base_tenant_domain:
        site.domain = new_domain
        site.save(update_fields=["domain"])


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
        parser.add_argument("--project-id", type=int, help="Set project ID")

        # Add billing plan limitation options
        BillingPlanManagement.add_arguments(parser, required=False)

    def handle(
        self,
        *args,
        new_domain: str,
        allowed_client_origins: list,
        project_id: int = None,
        **options
    ):
        with transaction.atomic():
            # Lock and retrieve tenant
            tenant: Tenant = Tenant.objects.filter(
                id=connection.tenant.id
            ).select_for_update().get()

            # Keep track of fields to save
            updated_fields = []
            limits = BillingPlanManagement.extract_limits_from_opts(options)

            if limits:
                BillingPlanManagement.set_tenant_limits(tenant, limits)
                updated_fields += limits.keys()

            if project_id is not None:
                tenant.project_id = project_id
                updated_fields.append("project_id")

            if new_domain is not None:
                update_domain(tenant, new_domain)
                updated_fields.append("domain_url")

            if allowed_client_origins is not None:
                tenant.allowed_client_origins = allowed_client_origins
                updated_fields.append("allowed_client_origins")

            if updated_fields:
                tenant.save(update_fields=updated_fields)
