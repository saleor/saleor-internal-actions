from datetime import datetime
from uuid import uuid4

import freezegun
import pytest

from saleor.order.models import Order
from tenants.limits.middleware import TenantPlanLimitMiddleware


def test_hard_limited_orders_are_blocked_when_exceeded(as_other_tenant):
    expected_error_data = {"resource": "Orders", "maximum": 0, "current": 0}
    tenant = as_other_tenant
    assert tenant.orders_hard_limited is True

    # Block creation of new orders
    tenant.max_order_count = 0

    # Should deny completing checkouts
    result = TenantPlanLimitMiddleware.is_mutation_allowed(tenant, "checkoutComplete")
    assert result.data == expected_error_data

    # Should deny creating new draft orders
    result = TenantPlanLimitMiddleware.is_mutation_allowed(tenant, "draftOrderCreate")
    assert result.data == expected_error_data


def test_non_hard_limited_orders_are_not_blocked_when_exceeding(as_other_tenant):
    tenant = as_other_tenant
    tenant.orders_hard_limited = False

    # Block creation of new orders
    tenant.max_order_count = 0

    # Should allow completing checkouts
    result = TenantPlanLimitMiddleware.is_mutation_allowed(tenant, "checkoutComplete")
    assert result is None

    # Should allow creating new draft orders
    result = TenantPlanLimitMiddleware.is_mutation_allowed(tenant, "draftOrderCreate")
    assert result is None


@pytest.mark.parametrize(
    "allowance_period, before_new_period_dt",
    [("daily", "2019-02-14T07:30:33+00:00"), ("monthly", "2019-01-31T07:30:33+00:00")],
)
def test_excludes_orders_outside_range(
    as_other_tenant, request, allowance_period, before_new_period_dt
):
    """
    When orders were created outside the current allowance period,
    they should not count towards hard limitation
    """
    now = "2019-02-15T07:30:33+00:00"

    tenant = as_other_tenant
    tenant.allowance_period = allowance_period

    # Only one order allowed
    tenant.max_order_count = 1
    assert Order.objects.exists() is False, "should not have any existing order"

    # Create one order for the tenant outside of current allowance period
    with freezegun.freeze_time(before_new_period_dt):
        order: Order = request.getfixturevalue("order")

    # Should allow creating new orders
    with freezegun.freeze_time(now):
        result = TenantPlanLimitMiddleware.is_mutation_allowed(
            tenant, "draftOrderCreate"
        )
        assert result is None, result.data

        # Creating a new order should block onwards
        order.pk = None
        order.token = uuid4()
        order.created = datetime.now()
        order.save()
        result = TenantPlanLimitMiddleware.is_mutation_allowed(
            tenant, "draftOrderCreate"
        )
        assert result is not None
        assert result.data == {"resource": "Orders", "maximum": 1, "current": 1}
