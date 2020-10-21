import mock
import pytest

from django.core.management import call_command, CommandError

from tenants.management.commands import rollback_tenant, restore_tenant

CMD = "rollback_tenant"


@mock.patch.object(restore_tenant, "MediaManager")
@mock.patch.object(restore_tenant, "call_command")
@mock.patch.object(restore_tenant.subprocess, "check_call")
@mock.patch.object(rollback_tenant.Command, "_drop_schema")
def test_rollback_tenant(
    mocked_drop_schema,
    mocked_check_call,
    mocked_call_command,
    mocked_media_manager,
    backup_archive_path,
    temporary_working_directory,
):
    call_command(CMD, backup_archive_path)

    mocked_drop_schema.assert_called_once()

    check_calls = mocked_check_call.call_args_list
    assert len(check_calls) == 2
    assert check_calls[0].args[0][0] == "pg_dump"
    assert check_calls[1].args[0][0] == "psql"

    mocked_call_command.assert_has_calls([
        mock.call("migrate_schemas", schema_name="mirumee"),
        mock.call("create_thumbnails")
    ])

    mocked_media_manager.return_value.upload.assert_called_once()


@mock.patch.object(restore_tenant, "call_command")
@mock.patch.object(restore_tenant.subprocess, "check_call", side_effect=[None, Exception, None])
@mock.patch.object(rollback_tenant.Command, "_drop_schema")
def test_rollback_tenant_dump_restore_fails(
    mocked_drop_schema,
    mocked_check_call,
    mocked_call_command,
    backup_archive_path,
    temporary_working_directory,
):
    with pytest.raises(CommandError):
        call_command(CMD, backup_archive_path)

    assert mocked_drop_schema.call_count == 2

    check_calls = mocked_check_call.call_args_list
    assert len(check_calls) == 3
    assert check_calls[0].args[0][0] == "pg_dump"
    assert check_calls[1].args[0][0] == "psql"
    assert check_calls[2].args[0][0] == "psql"

    mocked_call_command.assert_called_with("migrate_schemas", schema_name="mirumee")
