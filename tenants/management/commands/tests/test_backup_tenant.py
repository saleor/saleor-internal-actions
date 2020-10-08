import hashlib
from os.path import exists
from pathlib import Path
from tarfile import TarFile
from typing import Any, Dict, Tuple
from unittest import mock

import boto3
import pytest
from boto3_type_annotations import s3
from boto.utils import compute_md5
from django.core.management import call_command, CommandError
from moto import mock_s3

from tenants.management.commands import backup_tenant

CMD = "backup_tenant"


@pytest.fixture
def mocked_dump():
    """Prevent from running the dump when we don't need to as it is a heavy process."""
    with mock.patch.object(backup_tenant.Command, "_run_django_dump_data") as patched:
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
    expected_json_dump = testdir.tmpdir.join("_expected.json")

    # Run the django command to get the expected data
    call_command(
        "dumpdata", exclude=["tenants"], indent=2, output=str(expected_json_dump)
    )

    # Run the tenant dump command
    call_command(CMD, archive_path)

    assert archive_path.check()
    assert logs.messages == [f"INFO:Created archive at: {archive_path!s}"]

    with open(expected_json_dump, "rb") as fp:
        expected_hash = compute_md5(fp)
        fp.seek(0)
        assert '"model": "tenants"'.encode() not in fp.read()

    # Check once the gzip file is decompressed, it is still the same file
    # as the original
    with TarFile.gzopen(str(archive_path), mode="r") as fin:
        assert [m.name for m in fin.getmembers()] == ["schema.json", "media"]
        extract_dir.mkdir()

        fin.extractall(path=str(extract_dir))
        with open(extract_dir.join("schema.json"), "rb") as fp:
            actual_hash = compute_md5(fp)

    assert actual_hash == expected_hash


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


@pytest.mark.parametrize(
    "app_labels, excludes",
    [
        (["a", "b"], []),
        (["a", "b"], ["a"]),
        (["a", "b"], ["tenants", "b"]),
        ([], ["tenants"]),
    ],
)
def test_providing_custom_apps_to_include_or_exclude(
    app_labels,
    excludes,
    temporary_working_directory,
    mocked_upload_to_s3,
    mocked_media_backup,
    mocked_dump,
    mocked_compress,
    mock_directory_output,
):
    """The default excluded apps should always be excluded, no matter what."""

    args = []

    for item in app_labels:
        args += ["--restrict", item]

    for item in excludes:
        args += ["--exclude", item]

    call_command(CMD, temporary_working_directory, *args)
    mocked_dump.assert_called_once()
    expected_excludes = {*excludes, *backup_tenant.Command.DEFAULT_EXCLUDE_LIST}

    labels_sent: Tuple[str, ...]
    options_sent: Dict[str, Any]
    (labels_sent, options_sent) = mocked_dump.call_args

    assert labels_sent == tuple(app_labels)
    assert options_sent["exclude"] == expected_excludes


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

    assert logs.messages == [f"INFO:Created archive at: {str(wanted_archive_path)}"]

    wanted_archive_path.check()
    assert not exists(
        temporary_archive_path
    ), "No temporary archive should have been created"
