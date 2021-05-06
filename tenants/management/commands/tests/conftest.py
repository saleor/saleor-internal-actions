import logging
import os
from unittest import mock
from uuid import UUID

import pytest

from tenants.management import gzip_dump_manager
from tenants.management.commands import backup_tenant, restore_tenant

TEST_UUID = UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8")


class LoggingHandler(logging.Handler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.messages = []

    def emit(self, record: logging.LogRecord):
        self.messages.append(f"{record.levelname}:{record.msg}" % record.args)


@pytest.fixture
def logs():
    log_handler = LoggingHandler()
    gzip_dump_manager.logger.addHandler(log_handler)
    backup_tenant.logger.addHandler(log_handler)
    restore_tenant.logger.addHandler(log_handler)
    return log_handler


@pytest.fixture()
def temporary_working_directory(testdir):
    return testdir.tmpdir.join(TEST_UUID.hex)


@pytest.fixture()
def temporary_raw_schema_path(temporary_working_directory):
    return temporary_working_directory.join("schema.sql")


@pytest.fixture()
def temporary_raw_metadata_path(temporary_working_directory):
    return temporary_working_directory.join("metadata.json")


@pytest.fixture()
def archive_path(testdir):
    return testdir.tmpdir.join(f"{TEST_UUID.hex}.tar")


@pytest.fixture
def mock_directory_output(testdir, archive_path):
    with mock.patch("tempfile.gettempdir") as patched_out_dir:
        with mock.patch("tenants.management.gzip_dump_manager.uuid4") as patched_uuid4:
            patched_out_dir.return_value = str(testdir.tmpdir)
            patched_uuid4.return_value = TEST_UUID
            yield


@pytest.fixture
def backup_archive_path():
    return f"{os.getcwd()}/tenants/management/commands/tests/backup.tar"
