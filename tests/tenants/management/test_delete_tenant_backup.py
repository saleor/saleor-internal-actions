from unittest import mock

import pytest
from django.core.management import call_command
from django.db import connection
from tenant_schemas.postgresql_backend.base import FakeTenant

from tenants.management.commands import deletetenant

CMD = "deletetenant"


@mock.patch.object(deletetenant, "call_command")
@mock.patch.object(deletetenant.Tenant, "delete")
def test_tenant_is_properly_selected_and_isolated(
    mocked_tenant_delete, mocked_call_command, tenant_connection_keeper, test_tenant
):
    """
    Ensure when backing up, the tenant is set in the connection
    and the public schemas are disabled.
    """

    tenant = test_tenant
    called_asserts = []

    def assert_connection_is_properly_configured(*_args, **_kwargs):
        called_asserts.append(1)
        assert connection.tenant == tenant
        assert connection.schema_name == tenant.schema_name
        assert connection.include_public_schema is False
        assert connection.settings_dict["SCHEMA"] == tenant.schema_name

    mocked_call_command.side_effect = assert_connection_is_properly_configured
    original_create_backup_meth = deletetenant.Command._create_backup

    def assert_connection_is_properly_reverted_after_call(*args, **kwargs):
        original_create_backup_meth(*args, **kwargs)
        called_asserts.append(2)
        assert isinstance(connection.tenant, FakeTenant)
        assert connection.tenant.schema_name == "public"
        assert connection.schema_name == "public"
        assert connection.include_public_schema is True
        assert connection.settings_dict["SCHEMA"] == "public"

    with mock.patch.object(
        deletetenant.Command,
        "_create_backup",
        wraps=assert_connection_is_properly_reverted_after_call,
    ):
        call_command(CMD, tenant.domain_url, "-b", "s3://dummy/test")

    assert called_asserts == [1, 2]
    mocked_tenant_delete.assert_called_once_with()


@mock.patch.object(deletetenant.Tenant, "delete")
def test_backup_location_is_optional_when_not_backing_up(
    mocked_tenant_delete, test_tenant
):
    call_command(CMD, test_tenant.domain_url)
    mocked_tenant_delete.assert_called_once()


@mock.patch.object(deletetenant.Tenant, "delete")
@mock.patch.object(deletetenant, "call_command", wraps=lambda *_, **__: 1 / 0)
def test_tenant_is_not_deleted_when_backup_failed(
    mocked_call_command, mocked_tenant_delete, tenant_connection_keeper, test_tenant
):
    with pytest.raises(ZeroDivisionError):
        call_command(CMD, test_tenant.domain_url, "-b", "s3://dummy/test")

    mocked_call_command.assert_called_once()
    cmd_name, *_ = mocked_call_command.call_args[0]

    mocked_tenant_delete.assert_not_called()
    assert cmd_name == "backup_tenant"
