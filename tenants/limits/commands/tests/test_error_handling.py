import logging
from unittest import mock

import pytest
import requests
from django.core.management import call_command
from freezegun import freeze_time

from . import conftest as t


@pytest.mark.parametrize(
    "_name, response_side_effect, expected_error",
    [
        (
            "HTTP 503",
            t.mk_fake_response(status=503, content=b"Oops"),
            "Got a temporary error from server: {'status_code': 503}",
        ),
        ("Request Timeout", requests.Timeout, "Timed out: {}"),
    ],
)
@freeze_time("2019-03-15T07:30:33.511276+00:00")
def test_retries_when_503(
    caplog,
    tenant_connection_keeper,
    fake_auth,
    fake_sleep,
    fake_put_records,
    _name,
    response_side_effect,
    expected_error,
):
    """Ensures it retries when a temporary failure such as 503 or timeout occurs"""
    response_success = t.mk_fake_response(status=200, content=t.SUCCESS_RESPONSE)
    fake_put_records.side_effect = [response_side_effect, response_success]

    call_command("collect_metrics", *t.VALID_CMD_OPTS)

    expected_call = t.DEFAULT_ENDPOINT_CALL
    fake_put_records.assert_has_calls([expected_call, expected_call])

    fake_sleep.assert_called_once_with(t.RETRY_DELAY)

    caplog.set_level(logging.ERROR)
    assert len(caplog.records) == 2, caplog.text
    error = caplog.records[0]
    success = caplog.records[1]
    assert error.message == (
        "Temporary failure for sending tenants usage metrics, "
        f"will retry after 3 seconds: {expected_error}"
    )
    assert error.levelname == "ERROR"
    assert error.exc_info is not None
    assert success.message == "Target successfully received and handled 2 records"


@freeze_time("2019-03-15T07:30:33.511276+00:00")
def test_retries_when_503_retries_until_exhaustion(
    tenant_connection_keeper,
    fake_sleep,
    fake_put_records,
    fake_auth,
):
    """
    Ensures it retries until out of allowed attempt when a temporary failure
    such as 503 keeps on occurring
    """
    response_503 = t.mk_fake_response(status=503, content=b"Oops")
    fake_put_records.return_value = response_503

    with pytest.raises(RuntimeError) as exc:
        call_command("collect_metrics", *t.VALID_CMD_OPTS)

    assert exc.value.args == ("Exhausted maximum attempt count",)

    # Should have retried 4 times then gaven up
    expected_call = t.DEFAULT_ENDPOINT_CALL
    fake_put_records.assert_has_calls([expected_call] * t.MAX_RETRIES)

    # Should have slept 3 times
    fake_sleep.assert_has_calls([mock.call(t.RETRY_DELAY)] * (t.MAX_RETRIES - 1))


@freeze_time("2019-03-15T07:30:33.511276+00:00")
def test_abort_when_unrecoverable(
    tenant_connection_keeper,
    caplog,
    fake_sleep,
    fake_put_records,
    fake_auth,
):
    """Ensures it aborts when a permanent failure such as 400 occurs"""
    response_400 = t.mk_fake_response(status=400, content=b"Bad request!")
    fake_put_records.return_value = response_400

    with pytest.raises(requests.HTTPError) as exc:
        call_command("collect_metrics", *t.VALID_CMD_OPTS)

    assert exc.value.args == (
        "Received an unexpected status code",
        {"status_code": 400, "expected_code": 200},
    )

    # Only one call should have occurred
    fake_put_records.assert_has_calls([t.DEFAULT_ENDPOINT_CALL])

    # Should not trigger a delay
    fake_sleep.assert_not_called()

    # Nothing should have been logged
    caplog.set_level(logging.ERROR)
    assert len(caplog.records) == 0
