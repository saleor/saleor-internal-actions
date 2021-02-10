"""
This test file contains test cases related to query building from ``ExportRecord``
inputs.
"""
import logging

import pytest
from opentelemetry.sdk.metrics.export import ExportRecord, aggregate

from dogstatsd_metric_exporter import configuration, errors
from dogstatsd_metric_exporter.exporter import E_RECORD_TOO_LONG
from dogstatsd_metric_exporter.exporter import logger as exporter_logger


@pytest.mark.parametrize(
    "labels, expected",
    [
        [(("foo", "bar"),), ("foo:bar",)],
        [(("tag1", "abc"), ("tag2", "qwerty")), ("tag1:abc", "tag2:qwerty")],
    ],
)
def test_format_labels(
    meter,
    exporter,
    labels: tuple[tuple[str, str]],
    expected: tuple[str, ...],
    dummy_record,
):
    dummy_record.labels = labels
    actual = exporter.format_tags_from_record(dummy_record)
    assert actual == expected


def test_formats_metric_with_metric_labels_and_resource_attributes(
    meter, exporter, dummy_record
):
    expected = (
        "key_with_str_value:Some String",
        "key_with_int_value:123",
        "key_with_boolean:True",
        "foo:bar",
        "hello:world",
    )

    dummy_record.labels = (("foo", "bar"), ("hello", "world"))
    exporter.include_resource_attributes = True
    actual = exporter.format_tags_from_record(dummy_record)

    assert actual == expected


def test_returns_multiple_packets_when_does_not_fit(exporter, meter, resource):
    """
    Ensure that when a single metric is too long to fit with another metric,
    the metric gets assigned its own packet (sends multiple packets).
    """
    exporter.max_packet_length = 25

    aggregator = aggregate.SumAggregator()
    aggregator.update(1)
    aggregator.take_checkpoint()

    maximum_name_characters: int = exporter.max_packet_length - len(":1|c\n")

    very_long_name = "a" * maximum_name_characters
    very_long_metric = meter.create_counter(very_long_name, "description", "1", int)
    very_long_record = ExportRecord(very_long_metric, tuple(), aggregator, resource)

    short_metric = meter.create_counter("short_name", "", "1", int)
    short_record = ExportRecord(short_metric, tuple(), aggregator, resource)

    expected_very_long_entry = f"{very_long_name}:1|c\n"

    # Ensure a single very_long_record is properly handled
    results = list(exporter.format_records([very_long_record]))
    assert results == [expected_very_long_entry]

    # Ensure having a short record followed by a non-fitting very long record
    # triggers two packets:
    #   1. The smaller one
    #   2. The very long one
    results = list(exporter.format_records([short_record, very_long_record]))
    assert results == ["short_name:1|c\n", expected_very_long_entry]

    # Ensure having the very long record first and then a short one directly triggers
    # to send a packet
    results = list(exporter.format_records([very_long_record, short_record]))
    assert results == [expected_very_long_entry, "short_name:1|c\n"]


def test_skips_failing_records(
    meter, exporter, dummy_record, unsupported_record, log_patcher
):
    """
    Ensure that if a record fails to be formatted, it will drop the record
    and notify about it in the logger but will keep on proceeding with the rest.
    """
    messages = log_patcher.init(exporter_logger).start()
    error_logs: list[logging.LogRecord] = messages["ERROR"]

    # First record must fail, then need to skip it and continue to process
    records = [unsupported_record, dummy_record]

    # Ensure it raises the error if set to not fail silently
    assert exporter.fail_silently is False
    with pytest.raises(errors.UnsupportedAggregator) as exc:
        it = exporter.format_records(records)
        _formatted = list(it)

    # Ensure the correct record is failing
    assert exc.value.args[1] is aggregate.HistogramAggregator
    assert len(error_logs) == 0, "shouldn't have logged any error"

    # Ensure does not raise exception when told to fail silently
    exporter.fail_silently = True

    # Ensure it doesn't raise but logs the error
    it = exporter.format_records(records)
    results = list(it)

    # Retrieve the error log entry
    assert len(error_logs) == 1, "should have logged one and only one error"
    error = error_logs[0]
    assert error.exc_info is not None, "should have provided exc_info"

    # The expected exception must happen: histogram aggregator is unsupported
    exc_type, exc_value, _tb = error.exc_info
    assert exc_type is errors.UnsupportedAggregator
    assert exc_value.args[1] is aggregate.HistogramAggregator

    # The failed record must be dropped but the next one
    # still must be processed
    assert results == ["dummy:2|c\n"]


def test_drops_record_when_too_long_to_safely_send(
    meter,
    exporter,
    dummy_aggregator,
    resource,
    dummy_record,
    unsupported_record,
    log_patcher,
):
    """
    Ensure if a record is too long to send safely over UDP/UDS, the record
    is dropped and continues on processing the other records unless told to
    not fail silently.
    """
    exporter.max_packet_length = 25

    very_long_name = "a" * exporter.max_packet_length
    very_long_metric = meter.create_counter(very_long_name, "description", "1", int)
    very_long_record = ExportRecord(
        very_long_metric, tuple(), dummy_aggregator, resource
    )
    expected_formatted_very_long_record = f"{very_long_name}:2|c\n"

    messages = log_patcher.init(exporter_logger).start()
    error_logs: list[logging.LogRecord] = messages["ERROR"]

    # First record must fail, then need to skip it and continue to process
    records = [very_long_record, dummy_record]

    # Ensure it raises the error if set to not fail silently
    assert exporter.fail_silently is False
    with pytest.raises(errors.TooLongRecord) as exc:
        it = exporter.format_records(records)
        _formatted = list(it)

    # Ensure the correct record is failing
    assert exc.value.args[1] == expected_formatted_very_long_record
    assert len(error_logs) == 0, "shouldn't have logged any error"

    # Ensure does not raise exception when told to fail silently
    exporter.fail_silently = True

    # Ensure it doesn't raise but logs the error
    it = exporter.format_records(records)
    results = list(it)

    # Retrieve the error log entry
    assert len(error_logs) == 1, "should have logged one and only one error"
    error = error_logs[0]
    assert error.exc_info is not None, "should have provided exc_info"
    assert error.message == E_RECORD_TOO_LONG % {
        "length": len(expected_formatted_very_long_record),
        "max_length": exporter.max_packet_length,
    }

    # The failed record must be dropped but the next one
    # still must be processed
    assert results == ["dummy:2|c\n"]
