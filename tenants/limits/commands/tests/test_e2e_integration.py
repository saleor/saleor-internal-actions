import logging

import pytest
from django.core.management import call_command
from freezegun import freeze_time

from . import conftest as t


@pytest.mark.vcr(**t.VCR_CONFIG, decode_compressed_response=True)
@freeze_time("2019-03-15T07:30:33.511276+00:00")
def test_fully_successful(
    tenant_connection_keeper,
    caplog,
    fake_auth,
    fake_sleep,
):
    """Test case when no partial error was returned by the service API"""
    call_command("collect_metrics", *t.VALID_CMD_OPTS)

    # Should not trigger a delay
    fake_sleep.assert_not_called()

    # We are expecting success message
    assert "Target successfully received and handled 2 records" in caplog.text


@pytest.mark.vcr(**t.VCR_CONFIG, decode_compressed_response=True)
@freeze_time("2019-03-15T07:30:33.511276+00:00")
def test_partial_error(
    tenant_connection_keeper,
    caplog,
    fake_auth,
    fake_sleep,
):
    """Test case when no partial error was returned by the service API"""
    caplog.set_level(logging.WARNING)
    call_command("collect_metrics", *t.VALID_CMD_OPTS)

    # Should not trigger a delay
    fake_sleep.assert_not_called()

    # We are not partial error message (warning)
    expected_warning = (
        "Target successfully received 2 records but returned 2 errors: "
        '["Failed to match an environment for host'
    )
    assert expected_warning in caplog.text
