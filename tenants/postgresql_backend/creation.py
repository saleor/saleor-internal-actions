from typing import Type
from django.db.backends.postgresql.creation import (
    DatabaseCreation as BaseDatabaseCreation,
)
from django.db.models import Model
from django.db import connection
from tenant_schemas.utils import get_tenant_model

# The site_settings fixture is blocking us from using other extension than `.com`
TEST_DOMAIN = ".com"


def _get_tenant_domain(tenant_name: str) -> str:
    """Return a domain name for a given tenant schema name."""
    return f"{tenant_name}{TEST_DOMAIN}"


DEFAULT_TEST_TENANT = {
    # The site_settings fixture is blocking us from using other than "mirumee.com"
    # as default
    "schema_name": "mirumee",
    "domain_url": _get_tenant_domain("mirumee"),
    "allowed_client_origins": [
        "http://example.com",
        "https://sub.example.com",
        "http://www.example.com",
        "http://test.com",
        "http://www.test.com",
    ],
    "project_id": 23,
    "max_channel_count": -1,
    "max_staff_user_count": -1,
    "max_warehouse_count": -1,
    "max_sku_count": -1,
    "max_order_count": -1,
    "orders_hard_limited": False,
    "allowance_period": "monthly",
}

OTHER_TEST_TENANT = {
    "schema_name": "example",
    "domain_url": _get_tenant_domain("othertenant"),
    "project_id": 54,
    "max_channel_count": 2,
    "max_staff_user_count": 3,
    "max_warehouse_count": 4,
    "max_sku_count": 5,
    "max_order_count": 10,
    "orders_hard_limited": True,
    "allowance_period": "daily",
}


# Define the tenants to be created when running tests
# The first tenant in the list will be considered and used as the default one
TEST_TENANTS = [DEFAULT_TEST_TENANT, OTHER_TEST_TENANT]


class DatabaseCreation(BaseDatabaseCreation):
    @property
    def tenant_model(self) -> Type[Model]:
        return get_tenant_model()

    @property
    def site_model(self) -> Type[Model]:
        from django.contrib.sites.models import Site

        return Site

    def _create_test_tenants(self):
        """Create the test tenants and set the default in the connection.

        The default tenant is the first in the list of `TEST_TENANTS`."""
        default_tenant = None

        for tenant_data in reversed(TEST_TENANTS):
            self.connection.set_schema_to_public()

            test_tenant = self.tenant_model.objects.filter(**tenant_data).first()
            if test_tenant is None:
                test_tenant = self.tenant_model(**tenant_data)
                test_tenant.save(verbosity=0)  # NOQA

            self.connection.set_tenant(test_tenant)
            site = self.site_model.objects.get()
            site.domain = tenant_data["domain_url"]
            site.save(update_fields=["domain"])

    def create_test_db(
        self, verbosity=1, autoclobber=False, serialize=True, keepdb=False
    ):
        """Create the test database, run the migrations and create the test tenants.

        Calls the super method first, which will invoke the `migrate` command
        from `tenants.management` which will invoke `migrate_schemas` from
        the third party.
        """
        super().create_test_db(
            verbosity=verbosity,
            autoclobber=autoclobber,
            serialize=serialize,
            keepdb=keepdb,
        )
        cursor = connection.cursor()
        cursor.execute("CREATE EXTENSION IF NOT EXISTS hstore")
        cursor.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
        self._create_test_tenants()
