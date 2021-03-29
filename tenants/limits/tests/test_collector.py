from typing import List, Tuple
from unittest import mock

import pytest
from tenant_schemas.utils import tenant_context

from saleor.core.utils import random_data as populate

from .. import collector
from .connections import FakeConnection

# <schema_name>, <host>, <project_id>, <table>, <live_tuple_count>
T_STAT_ROW = Tuple[str, str, int, str, int]


@pytest.fixture
def dummy_postgres_stats_rows(test_tenant, other_tenant) -> List[T_STAT_ROW]:
    tenant_project_id = test_tenant.project_id
    other_project_id = other_tenant.project_id
    return [
        # (<schema_name>, <host>, <project_id>, <table>, <live_tuple_count>)
        ("mirumee", "mirumee.com", tenant_project_id, "product_productvariant", 4),
        ("mirumee", "mirumee.com", tenant_project_id, "channel_channel", 5),
        ("mirumee", "mirumee.com", tenant_project_id, "warehouse_warehouse", 6),
        ("mirumee", "mirumee.com", tenant_project_id, "order_order", 7),
        ("example", "othertenant.com", other_project_id, "channel_channel", 10),
        ("example", "othertenant.com", other_project_id, "warehouse_warehouse", 9),
        ("example", "othertenant.com", other_project_id, "order_order", 8),
        ("example", "othertenant.com", other_project_id, "product_productvariant", 7),
    ]


def test_collect_complex_metrics(tenant_connection_keeper, test_tenant, other_tenant):
    test_tenant_staff_count = 4
    other_tenant_staff_count = 2

    # Test tenant, 4 staff users
    populate.create_staff_users(how_many=test_tenant_staff_count, superuser=False)

    # Other tenant, 2 staff users
    with tenant_context(other_tenant):
        populate.create_staff_users(how_many=other_tenant_staff_count, superuser=False)

    # Create the manager
    manager = collector.TenantMetricManager()

    # Populate the metrics for each targeted tenant
    test_tenant_metrics = manager.create_tenant_metrics_container(
        schema_name=test_tenant.schema_name,
        host=test_tenant.domain_url,
        project_id=test_tenant.project_id,
    )
    other_tenant_metrics = manager.create_tenant_metrics_container(
        schema_name=other_tenant.schema_name,
        host=other_tenant.domain_url,
        project_id=other_tenant.project_id,
    )

    # Collect and update above metrics
    manager._collect_complex_metrics()

    assert test_tenant_metrics.staff_users == test_tenant_staff_count
    assert other_tenant_metrics.staff_users == other_tenant_staff_count


def test_collect_basic_stats_metrics(
    tenant_connection_keeper, test_tenant, other_tenant, dummy_postgres_stats_rows
):
    """Test ability to parse statistics properly"""
    fake_cursor = mock.MagicMock()
    fake_cursor.fetchall.return_value = dummy_postgres_stats_rows
    fake_cursor.start()

    fake_connection = FakeConnection(fake_cursor)

    with mock.patch.object(
        collector.TenantMetricManager,
        "get_connection",
        return_value=fake_connection,
    ):
        manager = collector.TenantMetricManager()
        manager._collect_basic_metrics()

    assert manager.as_list() == [
        {
            "channels": 5,
            "host": "mirumee.com",
            "orders": 7,
            "project_id": 23,
            "staff_users": 0,
            "variants": 4,
            "warehouses": 6,
        },
        {
            "channels": 10,
            "host": "othertenant.com",
            "orders": 8,
            "project_id": 54,
            "staff_users": 0,
            "variants": 7,
            "warehouses": 9,
        },
    ]
