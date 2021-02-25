from unittest.mock import patch

import pytest
from django.db import connection

from saleor.channel.models import Channel
from saleor.graphql.tests.utils import get_graphql_content
from tenants.limits.middleware import TenantPlanLimitMiddleware, channel_limit
from tenants.models import Tenant

from .queries import CREATE_CHANNEL

# Make a deep copy of the query set to prevent any side effect from mocking it
channel_limit.qs = channel_limit.qs.all()


@pytest.mark.parametrize(
    "mutation_name, tenant_field, resource_name",
    [
        ("staffCreate", "max_staff_user_count", "Staff Users"),
        ("productVariantCreate", "max_sku_count", "SKUs"),
        ("productCreate", "max_sku_count", "SKUs"),
        ("warehouseCreate", "max_warehouse_count", "Warehouses"),
        ("channelCreate", "max_channel_count", "Channels"),
    ],
)
def test_limitations(as_other_tenant, mutation_name, tenant_field, resource_name):
    """Ensure limitations are working as expected and querying proper resources"""
    tenant = as_other_tenant

    # Ensure there is no left over
    assert getattr(tenant, tenant_field) > 0

    # Set only one field to 0
    setattr(tenant, tenant_field, 0)

    # Should deny
    result = TenantPlanLimitMiddleware.is_mutation_allowed(tenant, mutation_name)
    assert result.data == {"resource": resource_name, "maximum": 0, "current": 0}


def test_minus_one_is_unlimited(as_other_tenant):
    tenant = as_other_tenant

    # Should allow when -1
    tenant.max_channel_count = -1
    result = TenantPlanLimitMiddleware.is_mutation_allowed(tenant, "channelCreate")
    assert result is None

    # Should deny when 0
    tenant.max_channel_count = 0
    result = TenantPlanLimitMiddleware.is_mutation_allowed(tenant, "channelCreate")
    assert result is not None
    assert result.data["resource"] == "Channels"


@pytest.mark.parametrize(
    "name, channel_count, is_error",
    [
        ("when nothing in db", 0, False),
        ("when exactly have one slot left", 1, False),
        ("when exactly the maximum count allowed", 2, True),
        ("when already exceeding, e.g. a race condition", 3, True),
    ],
)
def test_proper_behavior_different_count(
    as_other_tenant: Tenant,
    name,
    channel_count,
    is_error,
    super_user_other_tenant_api_client,
):
    """
    Ensure we have the expected and same behavior when less than the limit is set.

    The test checks the limit works as ``Count < Max``

    Limits are defined at ``tenants.postgresql_backend.creation.OTHER_TEST_TENANT``.
    """
    assert as_other_tenant.max_channel_count == 2, "test was designed for 2"

    channel_qs = Channel.objects.all()
    assert channel_qs.count() == 0

    def get_count(*_args, **_kwargs):
        return channel_count

    # Put a function instead of ``return_value`` as it makes it easier to put a breakpoint
    with patch.object(channel_limit.qs, "count", wraps=get_count) as mocked_qs_count:
        response = super_user_other_tenant_api_client.post_graphql(CREATE_CHANNEL)
        assert response.status_code == 200, response.content
        contents: dict = get_graphql_content(response, ignore_errors=True)

        mocked_qs_count.assert_called_once_with()
        mocked_qs_count.reset_mock()

        errors = contents.get("errors", [])
        results = contents["data"]["channelCreate"]

        if is_error is True:
            assert results is None, "user should not be created"
            assert len(errors) == 1
            assert errors[0]["message"] == "Reached plan limits of 2 Channels"
            assert channel_qs.count() == 0, "should have created nothing"
        else:
            assert errors == [], "should not have errors"
            assert results is not None, "should return created channel"
            assert results["channel"]["slug"] == "mychannel"
            assert channel_qs.count() == 1, "should be one"
