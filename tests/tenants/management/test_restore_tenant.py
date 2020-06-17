from pathlib import Path
from unittest import mock

import boto3
import pytest
from boto3_type_annotations import s3
from django.core.management import call_command, CommandError
from moto import mock_s3
from tenants.management.commands import restore_tenant
from .test_backup_tenant import CMD as backup_cmd

CMD = "restore_tenant"


@pytest.fixture
def mocked_run_restore():
    with mock.patch.object(restore_tenant.Command, "_run_django_load_data") as mocked:
        yield mocked


@pytest.fixture
def mocked_media_list():
    with mock.patch.object(restore_tenant.MediaManager, "_list_storage_dir") as patched:
        patched.return_value = [], []
        yield patched


def test_location_required(test_tenant):
    with pytest.raises(CommandError) as exc:
        call_command(CMD, bucket_name="abc")

    assert exc.value.args == ("Error: the following arguments are required: location",)


@mock_s3
def test_restore_from_bucket(
    tenant_connection_keeper,
    mocked_run_restore,
    mock_directory_output,
    mocked_media_list,
    test_tenant,
    archive_path,
    temporary_working_directory,
    temporary_raw_schema_path,
    logs,
):
    BUCKET_NAME = "tenants_dumps"
    FILENAME = "tenant_backup.tar.gz"

    connection: s3.Client = boto3.client("s3")
    connection.create_bucket(Bucket=BUCKET_NAME)

    s3_location = f"s3://{BUCKET_NAME}/{FILENAME}"
    call_command(backup_cmd, s3_location)

    with mock.patch("shutil.rmtree") as mocked_rmtree:
        call_command(CMD, s3_location)

    mocked_run_restore.assert_called_once()

    call_args, call_kwargs = mocked_run_restore.call_args
    assert call_args == (temporary_raw_schema_path,)

    mocked_rmtree.assert_called_once_with(
        Path(temporary_working_directory), ignore_errors=True
    )

    temporary_raw_schema_path.check()

    assert logs.messages == [
        f"INFO:Created archive at: {str(archive_path)}",
        f"INFO:Uploading archive to s3://tenants_dumps/tenant_backup.tar.gz...",
        f"INFO:Retrieving archive from s3://tenants_dumps/tenant_backup.tar.gz...",
        f"INFO:Extracting schema.json to {str(temporary_working_directory)}",
        f"INFO:Extracting media to {str(temporary_working_directory)}",
        f"INFO:Restoring the data...",
    ]


def test_restore_from_local_file(
    tenant_connection_keeper,
    testdir,
    mocked_run_restore,
    mock_directory_output,
    mocked_media_list,
    test_tenant,
    temporary_working_directory,
    temporary_raw_schema_path,
    logs,
):
    wanted_archive_path = testdir.tmpdir.join(f"backup.tar.gz")
    call_command(backup_cmd, wanted_archive_path)

    with mock.patch("shutil.rmtree") as mocked_rmtree:
        call_command(CMD, wanted_archive_path)

    mocked_run_restore.assert_called_once()

    call_args, call_kwargs = mocked_run_restore.call_args
    assert call_args == (temporary_raw_schema_path,)

    mocked_rmtree.assert_called_once_with(
        Path(temporary_working_directory), ignore_errors=True
    )

    temporary_raw_schema_path.check()

    assert logs.messages == [
        f"INFO:Created archive at: {str(wanted_archive_path)}",
        f"INFO:Extracting schema.json to {str(temporary_working_directory)}",
        f"INFO:Extracting media to {str(temporary_working_directory)}",
        f"INFO:Restoring the data...",
    ]


@mock.patch.object(restore_tenant.Site.objects, "get")
def test_restore_updates_site_domain_when_domain_is_changed(
    mocked_site,
    tenant_connection_keeper,
    testdir,
    mocked_run_restore,
    mock_directory_output,
    mocked_media_list,
    test_tenant,
    temporary_working_directory,
    temporary_raw_schema_path,
    logs,
):
    mocked_site = mocked_site.return_value
    mocked_site.domain = "outdated"

    wanted_archive_path = testdir.tmpdir.join(f"backup.tar.gz")
    call_command(backup_cmd, wanted_archive_path)

    with mock.patch("shutil.rmtree") as mocked_rmtree:
        call_command(CMD, wanted_archive_path)

    mocked_run_restore.assert_called_once()

    call_args, call_kwargs = mocked_run_restore.call_args
    assert call_args == (temporary_raw_schema_path,)

    mocked_rmtree.assert_called_once_with(
        Path(temporary_working_directory), ignore_errors=True
    )

    temporary_raw_schema_path.check()

    assert logs.messages == [
        f"INFO:Created archive at: {str(wanted_archive_path)}",
        f"INFO:Extracting schema.json to {str(temporary_working_directory)}",
        f"INFO:Extracting media to {str(temporary_working_directory)}",
        f"INFO:Restoring the data...",
        f"INFO:Updating outdated site domain...",
    ]

    assert mocked_site.domain == test_tenant.domain_url
