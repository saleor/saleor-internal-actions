import pytest
from django import db
from tenant_schemas.utils import get_public_schema_name, schema_context, tenant_context

from saleor.account.models import User
from saleor.graphql.tests.fixtures import TenantApiClient
from tenants.models import Tenant
from tenants.postgresql_backend.base import DatabaseWrapper

connection: DatabaseWrapper


@pytest.fixture
def tenant_connection_keeper(test_tenant):
    """
    Restore the original and unaltered tenant connection once the wrapped test is over.
    Useful when a test or the app changed the tenant connection schema.

    It will use a copy of the tenant to protect any alterations to the tenant
    from the connection object that would affect other tests

    pytest-django will revert any changes after the tests and all fixtures,
    but will not be reflected to the connection object.
    """
    untouched_tenant = Tenant.objects.get(pk=test_tenant.pk)
    yield
    db.connection.set_tenant(untouched_tenant)


@pytest.fixture
def super_user_other_tenant_api_client(other_tenant):
    with tenant_context(other_tenant):
        user_ = User.objects.create_superuser("othersuperuser@example.com", "pass")
        client_ = TenantApiClient(other_tenant, user=user_)
        return client_


@pytest.fixture
def as_other_tenant(other_tenant):
    with tenant_context(other_tenant):
        yield other_tenant


@pytest.fixture
def as_public():
    with schema_context(get_public_schema_name()):
        yield
