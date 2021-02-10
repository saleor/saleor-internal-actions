"""
This test file contains test cases related to the batch buffer.

Ensures queued batches packets are properly processed (happens when a batch failed
or multiple batches failed to be sent). As well as they are able to be dropped if the
buffer is too big.
"""
import logging
import unittest.mock

import pytest

from dogstatsd_metric_exporter.queue import W_TOO_MANY_BATCHES, Queue
from dogstatsd_metric_exporter.queue import logger as queue_logger


@pytest.fixture
def mocked_send_packet():
    mocker = unittest.mock.MagicMock()
    return mocker


@pytest.fixture
def batch_count_limit() -> int:
    return 3


@pytest.fixture
def queue(batch_count_limit, mocked_send_packet) -> Queue:
    return Queue(
        batch_count_limit=batch_count_limit,
        fail_silently=False,
        send_packet=mocked_send_packet,
    )


def test_flush_empty_buffer(queue, mocked_send_packet):
    """
    Ensure if the buffer is empty, nothing is done
    """
    queue.maybe_flush()
    mocked_send_packet.assert_not_called()


def test_flush_empty_batch(queue, mocked_send_packet):
    """
    Ensure when the buffer contains an empty batch, the batch is skipped.
    """
    queue.append([])
    queue.maybe_flush()

    # Should not have had to send anything
    mocked_send_packet.assert_not_called()


def test_flush_buffer(queue, mocked_send_packet):
    """
    Ensure the buffer is able to be flushed and is behaving as expected:
    - Sends the data as is,
    - Sends in FIFO order.
    """

    expected_calls = (
        unittest.mock.call("d"),
        unittest.mock.call("c"),
        unittest.mock.call("b"),
        unittest.mock.call("a"),
    )

    queue.append(["a", "b", "c"])
    queue.append(["d"])

    queue.maybe_flush()

    mocked_send_packet.assert_has_calls(calls=expected_calls, any_order=False)


def test_exception_while_flushing_after_success(queue, mocked_send_packet):
    """
    Ensure when any exception happening while flushing a packet causes to abort
    the flush.

    Previous packet and batch that was successful shall be removed, i.e.
    the buffer doesn't send a successful packet a second time.
    """

    queue.append(["0"])
    queue.append(["1", "2", "3"])
    queue.append(["c", "d"])

    # Flush successfully the last batch and the last packet of the first batch
    mocked_send_packet.side_effect = [None, None, None, RuntimeError("Oops")]

    with pytest.raises(RuntimeError) as exc:
        queue.maybe_flush()

    assert exc.value.args == ("Oops",)

    # Should send the last batch appended fully
    # then the first appended batch should fail in the middle,
    # "1" should never get send
    expected_calls = (
        unittest.mock.call("d"),
        unittest.mock.call("c"),
        unittest.mock.call("3"),
        unittest.mock.call("2"),  # Failed, "1" and "0" never happen
    )
    mocked_send_packet.assert_has_calls(expected_calls, any_order=False)
    mocked_send_packet.reset_mock()

    # Retry flushing the buffer
    mocked_send_packet.side_effect = None
    result_code = queue.maybe_flush()
    assert result_code.name == "SUCCESS", "should be success"

    # The new attempt should only send the packet that was unsuccessful
    # as well as batches that were never attempted due to unexpected failure
    expected_calls = (
        unittest.mock.call("1"),
        unittest.mock.call("0"),
    )
    mocked_send_packet.assert_has_calls(expected_calls)


def test_fail_silently_does_not_raise_exception(queue, mocked_send_packet, log_patcher):
    """
    When set to fail silently (``True``) any exception while flushing
    shall be dispatched to the logger and return ``1`` to notify the caller
    about the failure.
    """
    queue.fail_silently = True
    mocked_send_packet.side_effect = RuntimeError("Oops")

    queue.append(["foo"])

    with log_patcher.init(queue_logger) as messages:
        result_code = queue.maybe_flush()

    mocked_send_packet.assert_called_with("foo")
    assert result_code.name == "FAILURE", "should be failure"

    errors = messages.get("ERROR", [])
    assert len(errors) == 1, f"unexpected count in {errors}"

    error: logging.LogRecord = errors[0]
    assert error.name == "dogstatsd_metric_exporter.queue"
    assert error.message == "Failed to flush the buffer"
    assert error.exc_info is not None, "should have passed exc_info"

    exc_type, exc_value, _tb = error.exc_info
    assert exc_type is RuntimeError
    assert exc_value.args == ("Oops",)


def test_drop_oldest_batch_when_queue_full(queue, log_patcher, batch_count_limit):
    """
    Ensure that when the limit of batches in buffer is exceeded,
    the oldest batch that was added is dropped for the new batch
    to be added.
    """
    assert batch_count_limit == 3

    messages = log_patcher.init(queue_logger).start()
    warnings: list[logging.LogRecord] = messages["WARNING"]

    queue.append(["a"])  # 1
    queue.append(["b"])  # 2
    queue.append(["c"])  # 3

    # Ensure no batch is dropped when the batch count is the same
    # as the count limit
    assert len(warnings) == 0, "should not have raised a warning"
    assert queue._buffer == [["a"], ["b"], ["c"]]

    # Overflow the buffer, should raise a warning and drop the oldest
    # batch
    queue.append(["d"])
    assert len(warnings) == 1, "should have warned about dropping a packet"
    warning = warnings[0]
    assert warning.message == W_TOO_MANY_BATCHES
    assert queue._buffer == [["b"], ["c"], ["d"]]
