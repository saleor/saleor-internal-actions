from . import queries


def test_limited_tenant(as_other_tenant, staff_api_client):
    assert as_other_tenant.max_channel_count == 2
    assert as_other_tenant.max_staff_user_count == 3
    assert as_other_tenant.max_warehouse_count == 4
    assert as_other_tenant.max_sku_count == 5

    limits = queries.execute_query(staff_api_client, queries.ALLOWED_USAGE_QUERY)
    assert limits["allowedUsage"] == {
        "channels": 2,
        "orders": None,
        "staffUsers": 3,
        "warehouses": 4,
        "productVariants": 5,
    }


def test_unlimited_tenant(test_tenant, staff_api_client):
    assert test_tenant.max_channel_count == -1
    assert test_tenant.max_staff_user_count == -1
    assert test_tenant.max_warehouse_count == -1
    assert test_tenant.max_sku_count == -1

    limits = queries.execute_query(staff_api_client, queries.ALLOWED_USAGE_QUERY)
    assert limits["allowedUsage"] == {
        "channels": None,
        "orders": None,
        "staffUsers": None,
        "warehouses": None,
        "productVariants": None,
    }
