from unittest.mock import patch, MagicMock

import pytest
from django.core.management import call_command
from tenants.management.commands.createtenant import Command
from tenants.management.commands.tests.conftest import get_limits_fields
from tenants.models import Tenant

CMD = "createtenant"


@pytest.fixture
def mocked_create_schema() -> MagicMock:
    with patch.object(Command, "create_schema") as mocked:
        yield mocked


@pytest.mark.parametrize(
    "name, limit_opts, expected",
    [
        (
            "provide all limit options",
            (
                "--channels",
                "10",
                "--products",
                "9",
                "--warehouses",
                "8",
                "--staff",
                "7",
            ),
            {
                "max_channel_count": 10,
                "max_sku_count": 9,
                "max_warehouse_count": 8,
                "max_staff_user_count": 7,
            },
        ),
        (
            "provide partially limit options, expect unlimited for missing options",
            (
                "--channels",
                "10",
                "--products",
                "9",
            ),
            {
                "max_channel_count": 10,
                "max_sku_count": 9,
                "max_warehouse_count": -1,
                "max_staff_user_count": -1,
            },
        ),
        (
            "provide no limit options, expect unlimited",
            (),
            {
                "max_channel_count": -1,
                "max_sku_count": -1,
                "max_warehouse_count": -1,
                "max_staff_user_count": -1,
            },
        ),
    ],
)
def test_create_tenant_with_limits_set(
    as_public, mocked_create_schema, name, limit_opts, expected
):
    domain = "my.tenant.test"

    # Check does not exist yet
    tenant_qs = Tenant.objects.filter(domain_url=domain, schema_name="mytenanttest")
    assert tenant_qs.exists() is False, "should not be existing"

    call_command(
        CMD, "my.tenant.test", "-s", "mytenanttest", "--project-id", "34", *limit_opts
    )

    fields = get_limits_fields()

    # Check tenant and the schema are created
    mocked_create_schema.assert_called_once()
    assert tenant_qs.exists() is True, "should exist"

    # Check limits are set
    actual = tenant_qs.values(*fields).get()
    assert actual == expected


def test_create_tenant_allows_missing_project_id(as_public, mocked_create_schema):
    domain = "my.tenant.test"

    # Check does not exist yet
    tenant_qs = Tenant.objects.filter(domain_url=domain, schema_name="mytenanttest")
    assert tenant_qs.exists() is False, "should not be existing"

    call_command(
        CMD, "my.tenant.test", "-s", "mytenanttest"
    )

    # Check tenant and the schema are created, project ID should be -1
    mocked_create_schema.assert_called_once()
    tenant = tenant_qs.get()
    assert tenant.project_id == -1
