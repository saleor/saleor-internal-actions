import json
from typing import Dict, Optional
from unittest.mock import MagicMock, patch

import pytest
from django.core.management import call_command

from tenants.limits import models as billing_models
from tenants.management.commands.createtenant import Command
from tenants.models import Tenant

CMD = "createtenant"


@pytest.fixture
def mocked_create_schema() -> MagicMock:
    with patch.object(Command, "create_schema") as mocked:
        yield mocked


@pytest.mark.parametrize(
    "name, limit_opts",
    [
        (
            "provide all limit options",
            {
                "orders_hard_limited": True,
                "allowance_period": "weekly",
                "max_channel_count": 10,
                "max_sku_count": 9,
                "max_warehouse_count": 8,
                "max_staff_user_count": 7,
                "max_order_count": 6,
            },
        ),
        (
            "provide partially limit options, expect unlimited for missing options",
            {
                "max_channel_count": 10,
                "max_sku_count": 9,
            },
        ),
        (
            "provide no limit options, expect unlimited",
            {},
        ),
        (
            "provide null",
            None,
        )
    ],
)
def test_create_tenant_with_limits_set(
    as_public, mocked_create_schema, name, limit_opts: Optional[Dict]
):
    domain = "my.tenant.test"

    expected = limit_opts.copy() if limit_opts is not None else {}

    # Default values when missing
    expected.setdefault("orders_hard_limited", False)
    expected.setdefault("allowance_period", "monthly")
    expected.setdefault("max_channel_count", -1)
    expected.setdefault("max_sku_count", -1)
    expected.setdefault("max_warehouse_count", -1)
    expected.setdefault("max_staff_user_count", -1)
    expected.setdefault("max_order_count", -1)

    # Check does not exist yet
    tenant_qs = Tenant.objects.filter(domain_url=domain, schema_name="mytenanttest")
    assert tenant_qs.exists() is False, "should not be existing"

    # Invoke
    if limit_opts is None:
        cmd_args = ()
    else:
        cmd_args = ("--billing-opts", json.dumps(limit_opts))
    call_command(
        CMD, "my.tenant.test", "-s", "mytenanttest", "--project-id", "34", *cmd_args
    )

    fields = billing_models.FIELDS

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

    call_command(CMD, "my.tenant.test", "-s", "mytenanttest")

    # Check tenant and the schema are created, project ID should be -1
    mocked_create_schema.assert_called_once()
    tenant = tenant_qs.get()
    assert tenant.project_id == -1
