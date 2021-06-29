from django.conf import settings
from django.db import connection

from tenants.limits.models import LIMIT_FIELDS
from tenants.management.argparse import LOCATION_TYPE, location_type
from tenants.management.billing_plan_manager import BillingOptionsParser
from tenants.management.commands import restore_tenant
from tenants.models import Tenant


class Command(restore_tenant.Command):
    help = "Create new tenant and dedicated database schema"

    @staticmethod
    def make_billing_opts_parser() -> BillingOptionsParser:
        billing_opts_parser = BillingOptionsParser()
        defaults = {field: -1 for field in LIMIT_FIELDS}
        billing_opts_parser.set_defaults(
            allowance_period="monthly", orders_hard_limited=False, **defaults
        )
        return billing_opts_parser

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

        billing_opts_parser = self.make_billing_opts_parser()
        billing_opts_parser.add_arguments(parser)

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
        billing_opts: BillingOptionsParser,
        **options
    ):
        domain_url = domain_url.lower()
        default_schema_name = domain_url.split(".")[0]

        # Prepare creation options for tenant
        tenants_args = {
            "domain_url": domain_url,
            "schema_name": schema or default_schema_name,
            "project_id": project_id,
            **billing_opts.parsed_options,
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
