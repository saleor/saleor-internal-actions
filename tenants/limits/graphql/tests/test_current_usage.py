from typing import List

import pytest
from _pytest.fixtures import FixtureRequest
from django.db import connection
from django.test.utils import CaptureQueriesContext

from . import queries


def get_django_sql_count_queries(captured: List[dict]) -> List[dict]:
    return [sql_query for sql_query in captured if "__count" in sql_query["sql"]]


@pytest.mark.parametrize(
    "field, expected_count, fixtures",
    [
        ("channels", 2, ["channel_USD", "channel_PLN"]),
        ("orders", 4, ["order_with_lines", "order_list"]),
        ("productVariants", 3, ["product_list_with_variants_many_channel"]),
        ("staffUsers", 3, ["staff_users"]),
        ("warehouses", 2, ["warehouses"]),
    ],
)
def test_partially_get_tenant_current_usage(
    as_other_tenant,
    request: FixtureRequest,
    staff_api_client,
    field: str,
    expected_count: int,
    fixtures: List[str],
):
    for fixture in fixtures:
        request.getfixturevalue(fixture)
    query = queries.PARTIAL_CURRENT_USAGE % {"field": field}

    with CaptureQueriesContext(connection) as context:
        result = queries.execute_query(staff_api_client, query)

    assert result["currentUsage"][field] == expected_count

    # Check only one ``COUNT(*) as "__count"`` query occurred
    # This ensures the resolver did not try to resolve everything at once
    # but only what was requested for
    sql_queries = context.captured_queries
    count_operations = get_django_sql_count_queries(sql_queries)
    assert len(count_operations) == 1


def test_retrieve_all_current_usages(
    as_other_tenant,
    staff_api_client,
    staff_users,
    product_with_two_variants,
    order_list,
    order,
):
    query = queries.ALL_CURRENT_USAGE

    with CaptureQueriesContext(connection) as context:
        result = queries.execute_query(staff_api_client, query)

    assert result == {
        "currentUsage": {
            "channels": 1,
            "orders": 4,
            "productVariants": 2,
            "staffUsers": 3,
            "warehouses": 1,
        }
    }

    # We expect django to do ``COUNT(*) as "__count"`` for all fields without duplicates
    sql_queries = context.captured_queries
    count_operations = get_django_sql_count_queries(sql_queries)
    assert len(count_operations) == 5
