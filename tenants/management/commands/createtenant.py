from django.conf import settings
from django.db import connection

from tenants.management.argparse import location_type, LOCATION_TYPE
from tenants.management.billing_plan_manager import BillingPlanManagement, T_LIMITS

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
        parser.add_argument(
            "--allowed-client-origins",
            dest="allowed_client_origins",
            help="List of allowed client origins",
            nargs="*",
        )
        parser.add_argument(
            "--project-id",
            help="The project primary key that is associated to the environment",
            required=False,
            default=-1,
        )

        # Add restoration options
        super().add_arguments(parser, add_location_arg=False)
        parser.set_defaults(bucket_name=settings.DEFAULT_BACKUP_BUCKET_NAME)

        # Add billing plan limitation options
        BillingPlanManagement.add_arguments(parser, required=False, default=-1)

    @staticmethod
    def create_schema(tenant: Tenant):
        tenant.create_schema()

    def handle(
        self,
        *_,
        domain_url: str,
        schema: str,
        project_id: int,
        location: LOCATION_TYPE = None,
        allowed_client_origins: list[str] = None,
        **options
    ):
        domain_url = domain_url.lower()
        default_schema_name = domain_url.split(".")[0]

        limits: T_LIMITS = BillingPlanManagement.extract_limits_from_opts(options)

        # Prepare creation options for tenant
        tenants_args = {
            "domain_url": domain_url,
            "schema_name": schema or default_schema_name,
            "project_id": project_id,
            **limits,
        }

        # Set allowed origins if specified
        if allowed_client_origins:
            tenants_args["allowed_client_origins"] = allowed_client_origins

        # Prepare the tenant with manual schema creation
        tenant = Tenant(**tenants_args)
        tenant.auto_create_schema = False

        # Download archive and extract the data
        if location:
            self.prepare_for_restore(location, **options)

        # Commit the tenant
        tenant.save()

        try:
            if location:
                connection.set_tenant(tenant)
                self.run_restore(skip_media=options["skip_media"])
            else:
                self.create_schema(tenant)
        except Exception as exc:
            tenant.delete()
            raise exc
