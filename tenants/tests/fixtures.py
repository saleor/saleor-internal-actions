import pytest

from saleor.account.models import User
from saleor.graphql.tests.fixtures import TenantApiClient

from tenant_schemas.utils import tenant_context, schema_context, get_public_schema_name
from tenants.postgresql_backend.base import DatabaseWrapper

connection: DatabaseWrapper


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
