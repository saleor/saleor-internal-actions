import hashlib
import uuid
from os.path import exists
from pathlib import Path
from tarfile import TarFile
from unittest import mock

import boto3
import pytest
from boto3_type_annotations import s3
from boto.utils import compute_md5
from django.core.management import call_command, CommandError
from django.apps import apps
from moto import mock_s3

from tenants.management.commands import backup_tenant

CMD = "backup_tenant"


@pytest.fixture
def mocked_dump():
    """Prevent from running the dump when we don't need to as it is a heavy process."""
    with mock.patch.object(backup_tenant, "run_dump_data") as patched:
        yield patched


@pytest.fixture
def mocked_compress():
    with mock.patch.object(backup_tenant.TenantDump, "compress_all") as patched:
        yield patched


@pytest.fixture
def mocked_upload_to_s3():
    with mock.patch.object(backup_tenant.Command, "_upload") as patched:
        yield patched


@pytest.fixture
def mocked_media_backup():
    with mock.patch.object(backup_tenant.Command, "_run_media_backup") as patched:
        yield patched


@pytest.fixture
def mocked_media_list():
    with mock.patch.object(backup_tenant.MediaManager, "_list_storage_dir") as patched:
        patched.return_value = [], []
        yield patched


def test_location_required(test_tenant):
    with pytest.raises(CommandError) as exc:
        call_command(CMD, bucket_name="abc")

    assert exc.value.args == ("Error: the following arguments are required: location",)


def test_dump_tenant(
    testdir,
    test_tenant,
    temporary_raw_schema_path,
    archive_path,
    mock_directory_output,
    mocked_media_list,
    logs,
):
    extract_dir = testdir.tmpdir.join("extracted")
    # Run the tenant dump command
    call_command(CMD, archive_path)

    assert archive_path.check()
    assert logs.messages == [
        "INFO:Dumping database...",
        "INFO:Done!",
        "INFO:Downloading media...",
        "INFO:Done!",
        "INFO:Compressing the backup...",
        f"INFO:Created archive at: {archive_path!s}",
    ]

    # Check once the gzip file is decompressed, it is still the same file
    # as the original
    with TarFile.gzopen(str(archive_path), mode="r") as fin:
        assert [m.name for m in fin.getmembers()] == [
            "schema.sql",
            "metadata.json",
            "media",
        ]
        extract_dir.mkdir()

        fin.extractall(path=str(extract_dir))

    with open(f"{extract_dir}/schema.sql") as f:
        dump = f.read()
        assert f'CREATE SCHEMA "{test_tenant.schema_name}"' in dump
        assert dump.count("CREATE SCHEMA") == 1
        assert 'TABLE "tenant"' not in dump


@mock.patch.object(backup_tenant.TenantDump, "add_metadata")
def test_dump_tenant_skip_media(
    mocked_add_metadata, archive_path, mocked_dump, mocked_compress, mocked_media_backup
):
    call_command(CMD, archive_path, "--skip_media")

    mocked_dump.assert_called_once()
    mocked_media_backup.assert_not_called()
    mocked_add_metadata.assert_called_once()
    kwargs = mocked_add_metadata.call_args.kwargs
    assert kwargs["skip_media"] is True


def test_not_providing_upload_filename_does_not_trigger_upload(
    mocked_upload_to_s3,
    mocked_media_backup,
    mocked_dump,
    mocked_compress,
    archive_path,
    mock_directory_output,
):
    """backup_tenant shouldn't try to upload the dump to the s3 bucket."""
    call_command(CMD, archive_path)
    mocked_dump.assert_called_once()
    mocked_compress.assert_called_once()
    mocked_upload_to_s3.assert_not_called()


def test_custom_compression_level(
    archive_path,
    mocked_upload_to_s3,
    mocked_media_backup,
    mocked_dump,
    mocked_compress,
    mock_directory_output,
):
    call_command(CMD, archive_path, compression_level=0)
    mocked_dump.assert_called_once()
    mocked_compress.assert_called_once_with(archive_path=Path(archive_path), level=0)
    mocked_upload_to_s3.assert_not_called()


@mock.patch("shutil.rmtree")
@mock_s3
def test_upload_to_s3_bucket(
    mocked_rmtree,
    temporary_working_directory,
    temporary_raw_schema_path,
    archive_path,
    mock_directory_output,
    mocked_media_list,
    logs,
):
    BUCKET_NAME = "tenants_dumps"
    FILENAME = "tenant_backup.tar.gz"

    connection: s3.Client = boto3.client("s3")
    connection.create_bucket(Bucket=BUCKET_NAME)

    options = (f"s3://{BUCKET_NAME}/{FILENAME}",)
    call_command(CMD, *options)

    # should have create a temporary schema dump
    temporary_raw_schema_path.check()

    mocked_rmtree.assert_called_once_with(
        Path(temporary_working_directory), ignore_errors=True
    )

    assert logs.messages == [
        "INFO:Dumping database...",
        "INFO:Done!",
        "INFO:Downloading media...",
        "INFO:Done!",
        "INFO:Compressing the backup...",
        f"INFO:Created archive at: {str(archive_path)}",
        "INFO:Uploading archive to s3://tenants_dumps/tenant_backup.tar.gz...",
    ]

    obj_data = connection.get_object(Bucket=BUCKET_NAME, Key=FILENAME)
    assert obj_data["ContentType"] == "application/x-gzip"
    body = obj_data["Body"].read()
    assert isinstance(body, bytes)

    with open(archive_path, "rb") as original_fp:
        expected_md5, *_ = compute_md5(original_fp)

    actual_md5 = hashlib.md5(body).hexdigest()
    assert actual_md5 == expected_md5


@mock.patch("shutil.rmtree")
@mock_s3
def test_save_to_local(
    mocked_rmtree,
    testdir,
    temporary_working_directory,
    temporary_raw_schema_path,
    archive_path,
    mock_directory_output,
    mocked_media_list,
    logs,
):
    wanted_archive_path = testdir.tmpdir.join("backup.tar.gz")
    temporary_archive_path = archive_path

    options = (wanted_archive_path,)
    call_command(CMD, *options)

    # should have create a temporary schema dump
    temporary_raw_schema_path.check()

    mocked_rmtree.assert_called_once_with(
        Path(temporary_working_directory), ignore_errors=True
    )

    assert logs.messages == [
        "INFO:Dumping database...",
        "INFO:Done!",
        "INFO:Downloading media...",
        "INFO:Done!",
        "INFO:Compressing the backup...",
        f"INFO:Created archive at: {str(wanted_archive_path)}",
    ]

    wanted_archive_path.check()
    assert not exists(
        temporary_archive_path
    ), "No temporary archive should have been created"
