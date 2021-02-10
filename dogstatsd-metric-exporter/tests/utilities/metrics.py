from opentelemetry.metrics import Meter
from opentelemetry.sdk.metrics.export import ExportRecord, aggregate
from opentelemetry.sdk.resources import Resource


def create_sum_record(
    meter: Meter, resource: Resource, *, name, values: list[int]
) -> ExportRecord:
    aggregator = aggregate.SumAggregator()
    for value in values:
        aggregator.update(value)
    aggregator.take_checkpoint()

    counter = meter.create_counter(name, "", "1", int)
    record = ExportRecord(counter, tuple(), aggregator, resource)
    return record
