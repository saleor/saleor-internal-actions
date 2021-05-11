from typing import List, Tuple
from unittest import mock

import pytest
from tenant_schemas.utils import tenant_context

from tenants.limits.commands import collect_metrics as collect_metrics_command
from tenants.tests import datasets

from .connections import FakeConnection

# <schema_name>, <host>, <project_id>, <is_daily>, <table>, <live_tuple_count>
T_STAT_ROW = Tuple[str, str, int, bool, str, int]


@pytest.fixture
def dummy_postgres_stats_rows(test_tenant, other_tenant) -> List[T_STAT_ROW]:
    tenant_project_id = test_tenant.project_id
    other_project_id = other_tenant.project_id
    # fmt: off
    return [
        # (<schema_name>, <host>, <project_id>, <is_daily>, <table>, <live_tuple_count>)
        ("mirumee", "mirumee.com", tenant_project_id, False, "product_productvariant", 4),
        ("mirumee", "mirumee.com", tenant_project_id, False, "channel_channel", 5),
        ("mirumee", "mirumee.com", tenant_project_id, False, "warehouse_warehouse", 6),
        ("example", "othertenant.com", other_project_id, False, "channel_channel", 10),
        ("example", "othertenant.com", other_project_id, False, "warehouse_warehouse", 9),
        ("example", "othertenant.com", other_project_id, False, "product_productvariant", 7),
    ]
    # fmt: on


def test_collect_complex_metrics(
    tenant_connection_keeper, metric_containers, other_tenant
):
    test_tenant_staff_count, test_tenant_orders = 4, 6
    other_tenant_staff_count, other_tenant_orders = 2, 1

    # Test tenant, 4 staff users
    datasets.create_users(how_many=test_tenant_staff_count, is_staff=True)
    datasets.create_orders(how_many=test_tenant_orders)

    # Other tenant, 2 staff users
    with tenant_context(other_tenant):
        datasets.create_users(how_many=other_tenant_staff_count, is_staff=True)
        datasets.create_orders(how_many=other_tenant_orders)

    # Create the manager
    manager, test_tenant_metrics, other_tenant_metrics = metric_containers

    # Collect and update above metrics
    manager._collect_complex_metrics()

    assert test_tenant_metrics.staff_users == test_tenant_staff_count
    assert other_tenant_metrics.staff_users == other_tenant_staff_count

    assert test_tenant_metrics.orders == test_tenant_orders
    assert other_tenant_metrics.orders == other_tenant_orders


def test_collect_basic_stats_metrics(
    tenant_connection_keeper, test_tenant, other_tenant, dummy_postgres_stats_rows
):
    """Test ability to parse statistics properly"""
    fake_cursor = mock.MagicMock()
    fake_cursor.fetchall.return_value = dummy_postgres_stats_rows
    fake_cursor.start()

    fake_connection = FakeConnection(fake_cursor)

    manager = collect_metrics_command.make_default_manager()
    with mock.patch.object(
        collect_metrics_command.TenantMetricManager,
        "get_connection",
        return_value=fake_connection,
    ):
        manager._collect_basic_metrics()

    assert manager.as_list() == [
        {
            "channels": 5,
            "host": "mirumee.com",
            "project_id": 23,
            "variants": 4,
            "warehouses": 6,
            # not counted keys
            "staff_users": 0,
            "orders": 0,
        },
        {
            "channels": 10,
            "host": "othertenant.com",
            "project_id": 54,
            "variants": 7,
            "warehouses": 9,
            # not counted keys
            "staff_users": 0,
            "orders": 0,
        },
    ]
