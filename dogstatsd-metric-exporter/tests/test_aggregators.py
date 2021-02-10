"""
This test file contains check cases for OpenTelemetry aggregators (SumAggregator,
ValueObserver, etc.).

They check the Exporter properly handles the aggregators and returns the expected
result (StatsD query).
"""

import pytest
from opentelemetry.sdk.metrics.export import ExportRecord, aggregate

from dogstatsd_metric_exporter import errors


def test_convert_from_sum(exporter, meter, labels, resource):
    int_metric = meter.create_counter("int", "description1", "integer", int)
    float_metric = meter.create_counter("float", "description3", "float", float)

    int_sum_aggregator = aggregate.SumAggregator()
    int_sum_aggregator.update(3)
    int_sum_aggregator.update(2)
    int_sum_aggregator.take_checkpoint()

    float_sum_aggregator = aggregate.SumAggregator()
    float_sum_aggregator.update(3.14)
    float_sum_aggregator.take_checkpoint()

    records = [
        ExportRecord(int_metric, labels, int_sum_aggregator, resource),
        ExportRecord(float_metric, labels, float_sum_aggregator, resource),
    ]

    packet_1_expected = (
        "int:5|c|#build_id:512,environment:staging\n"
        "float:3.14|c|#build_id:512,environment:staging\n"
    )

    it = exporter.format_records(records)
    results: list[list[str]] = list(it)
    assert results == [packet_1_expected]


@pytest.mark.parametrize("invalid_value", (None, "string"))
def test_last_value_aggregator_invalid_value(exporter, meter, resource, invalid_value):
    """
    Ensure an exception is raised whenever an invalid or unknown value is passed
    """
    metric = meter.create_valuerecorder("last_sent_length", "", "bytes", value_type=int)
    aggregator = aggregate.LastValueAggregator()
    aggregator.update(invalid_value)
    aggregator.take_checkpoint()

    record = ExportRecord(metric, tuple(), aggregator, resource)

    with pytest.raises(errors.UnsupportedValueType) as exc:
        exporter.format_record(record)

    # The invalid type should be passed as Type object to the exception instance
    assert issubclass(exc.value.args[1], type(invalid_value))


def test_min_max_count_aggregator(exporter, meter, resource):
    """
    Ensure the value taken from MinMaxSumCountAggregator is the sum of all values
    and is formatted as gauge.
    """
    expected = "min_max:6|g\n"

    metric = meter.create_valuerecorder("min_max", "", "1", value_type=int)
    aggregator = aggregate.MinMaxSumCountAggregator()
    aggregator.update(1)
    aggregator.update(2)
    aggregator.update(3)
    aggregator.take_checkpoint()

    record = ExportRecord(metric, tuple(), aggregator, resource)
    actual = exporter.format_record(record)
    assert actual == expected


def test_histogram_aggregator_raises_exception(exporter, meter, resource):
    metric = meter.create_valuerecorder("counter", "", "1", value_type=int)
    aggregator = aggregate.HistogramAggregator()
    aggregator.update(1)
    aggregator.take_checkpoint()

    record = ExportRecord(metric, tuple(), aggregator, resource)

    with pytest.raises(errors.UnsupportedAggregator) as exc:
        exporter.format_record(record)

    # The value of the exception instance must be the aggregator class type
    assert exc.value.args[1] is aggregate.HistogramAggregator
