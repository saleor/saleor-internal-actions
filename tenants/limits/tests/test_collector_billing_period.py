"""Test cases ensuring data is not counted when outside billing period"""

from freezegun import freeze_time
from tenant_schemas.utils import tenant_context

from saleor.order.models import Order
from datetime import datetime

from tenants.models import Tenant


@freeze_time("2019-03-15T07:30:33+00:00")
def test_daily_plans_orders(
    as_other_tenant: Tenant, channel_PLN, request, tenant_connection_keeper
):
    # Get manager from fixture using frozen date
    manager, monthly_tenant, daily_tenant = request.getfixturevalue("metric_containers")

    # Check manager settings
    assert as_other_tenant.allowance_period == "daily"
    assert manager.start_day_datetime == "2019-03-15T00:00:00+00:00"
    assert daily_tenant.is_daily is True

    def make_next_order(token: str, created: datetime):
        with tenant_context(as_other_tenant):
            Order.objects.create(channel=channel_PLN, token=token, created=created)

    now = datetime.fromisoformat("2019-03-15T07:30:33+00:00")
    yesterday = datetime.fromisoformat("2019-03-14T07:30:33+00:00")
    after_midnight = datetime.fromisoformat("2019-03-15T00:30:33+00:00")

    # No orders should imply no increment
    manager._collect_complex_metrics()
    assert daily_tenant.orders == 0

    # Orders before today should be excluded
    make_next_order("yesterday", yesterday)
    manager._collect_complex_metrics()
    assert daily_tenant.orders == 0

    # Orders for today should be included
    make_next_order("today, after midnight", after_midnight)
    make_next_order("now", now)
    manager._collect_complex_metrics()
    assert daily_tenant.orders == 2


@freeze_time("2019-03-15T07:30:33+00:00")
def test_monthly_plans_orders(
    test_tenant, channel_PLN, request, tenant_connection_keeper
):
    # Get manager from fixture using frozen date
    manager, monthly_tenant, daily_tenant = request.getfixturevalue("metric_containers")

    # Check manager settings
    assert test_tenant.allowance_period == "monthly"
    assert manager.start_day_datetime == "2019-03-15T00:00:00+00:00"
    assert manager.start_month_datetime == "2019-03-01T00:00:00+00:00"
    assert monthly_tenant.is_daily is False

    def make_next_order(token: str, created: datetime):
        with tenant_context(test_tenant):
            Order.objects.create(channel=channel_PLN, token=token, created=created)

    last_month = datetime.fromisoformat("2019-02-15T00:30:33+00:00")
    now = datetime.fromisoformat("2019-03-15T07:30:33+00:00")
    yesterday = datetime.fromisoformat("2019-03-14T07:30:33+00:00")
    beginning_month = datetime.fromisoformat("2019-03-01T07:30:33+00:00")

    # No orders should imply no increment
    manager._collect_complex_metrics()
    assert monthly_tenant.orders == 0

    # Orders before this month should be excluded
    make_next_order("last month", last_month)
    manager._collect_complex_metrics()
    assert monthly_tenant.orders == 0

    # Orders for today and current month should be included
    make_next_order("today", now)
    make_next_order("yesterday", yesterday)
    make_next_order("beginning of the month", beginning_month)
    manager._collect_complex_metrics()
    assert monthly_tenant.orders == 3
