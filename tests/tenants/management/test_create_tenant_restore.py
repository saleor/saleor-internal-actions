from unittest import mock

import pytest
from django.core.management import call_command, CommandError
from django.db import connection
from tenants.management.argparse import S3Options
from tenants.management.commands import createtenant


CMD = "createtenant"


@mock.patch.object(createtenant.Command, "run_restore")
@mock.patch.object(createtenant.Command, "_get_dump_from_s3")
@mock.patch.object(createtenant, "Tenant")
def test_tenant_is_properly_selected(
    mocked_tenant, _, mocked_call_command, tenant_connection_keeper
):
    """
    Ensure when backing up, the tenant is set in the connection
    and the public schemas are disabled.
    """

    tenant = mocked_tenant.return_value
    called_asserts = []

    def assert_connection_is_properly_configured(*_args, **_kwargs):
        called_asserts.append(1)
        assert connection.tenant == tenant
        assert connection.schema_name == tenant.schema_name
        assert connection.include_public_schema is True
        assert connection.settings_dict["SCHEMA"] == tenant.schema_name

    mocked_call_command.side_effect = assert_connection_is_properly_configured

    call_command(CMD, tenant.domain_url, "-r", "s3://dummy/test")

    assert called_asserts == [1]
    tenant.save.assert_called_once_with()


@mock.patch.object(createtenant.Tenant, "save")
def test_restore_location_is_optional_when_not_backing_up(
    mocked_tenant_save, test_tenant
):
    call_command(CMD, test_tenant.domain_url)
    mocked_tenant_save.assert_called_once()


@mock.patch.object(createtenant.Tenant, "save")
@mock.patch.object(createtenant.Tenant, "delete")
@mock.patch.object(createtenant.Command, "run_restore", wraps=lambda *_, **__: 1 / 0)
@mock.patch.object(createtenant.Command, "_get_dump_from_s3")
def test_tenant_is_deleted_when_restore_failed(
    mocked_get_dump_from_s3,
    mocked_tenant_delete,
    mocked_tenant_save,
    _,
    tenant_connection_keeper,
    test_tenant,
):
    with pytest.raises(ZeroDivisionError):
        call_command(CMD, test_tenant.domain_url, "-r", "s3://dummy/test")

    mocked_get_dump_from_s3.assert_called_once_with(
        opts=S3Options(Bucket="dummy", Key="test")
    )
    mocked_tenant_save.assert_called()
    mocked_tenant_delete.assert_called()
