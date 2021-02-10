import unittest.mock

import pytest

from dogstatsd_metric_exporter.exporter import E_FAILED_SEND_PACKET

from .utilities.metrics import create_sum_record


def test_no_incoming_records(exporter, mock_flush):
    """
    Ensure when no records are passed to export,
    flushes the buffer and skip query building
    """
    mocked_flush = mock_flush(None)
    exporter.export([])
    mocked_flush.assert_called_once()


def test_send_records(meter, resource, exporter, mock_flush, mocked_xmit_packet):
    """
    Ensure the buffer is flushed before and after processing records
    to export.
    """
    # Disable telemetry as it will create noise
    exporter._client.disable_telemetry()

    # Mock flush but wrap it to the original method so it can call `_xmit_packet``
    mocked_flush = mock_flush(True)

    record1 = create_sum_record(meter, resource, name="batch1", values=[1])
    record1_formatted: str = exporter.format_record(record1)

    record2 = create_sum_record(meter, resource, name="batch2", values=[3])
    record2_formatted: str = exporter.format_record(record2)

    # Add first record batch into buffer, it must get flushed before processing
    # the records to send
    exporter.append_to_buffer([record1_formatted])

    # Export the second batch while buffer is not empty
    exporter.export([record2])

    # Ensure the flush happened two times and triggered emission of the packets
    assert mocked_flush.call_count == 2
    mocked_xmit_packet.assert_has_calls(
        [
            unittest.mock.call(record1_formatted, telemetry=True),
            unittest.mock.call(record2_formatted, telemetry=True),
        ]
    )


def test_send_records_handles_exception_while_sending(
    meter, resource, exporter, mock_flush, mocked_xmit_packet
):
    """
    Ensure that if ``_xmit_packet`` fails, the exception is silent
    """
    record = create_sum_record(meter, resource, name="batch", values=[1])
    record_formatted: str = exporter.format_record(record)

    # Mock flush but wrap it to the original method so it can call `_xmit_packet``
    mocked_flush = mock_flush(True)

    # Make ``_xmit_packet`` report an exception
    mocked_xmit_packet.return_value = False

    # Ensure errors are not silent and the exception actually occurs
    assert exporter._queue.fail_silently is False
    assert exporter.fail_silently is False

    # Trigger the exception
    with pytest.raises(RuntimeError) as exc:
        exporter.export([record])

    assert exc.value.args == (E_FAILED_SEND_PACKET,)

    # Empty the buffer from previous failed export
    exporter._queue._buffer.clear()

    # Check the exception is silent and it keeps the failed batch in buffer
    exporter._queue.fail_silently = exporter.fail_silently = True
    result = exporter.export([record])
    assert result.name == "FAILURE", "should be flagged as failure"
    assert exporter._queue._buffer == [[record_formatted]], "should be in the buffer"
