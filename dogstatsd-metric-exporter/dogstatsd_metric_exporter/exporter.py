import logging
from typing import Generator, ItemsView, Sequence

from datadog.dogstatsd import base
from opentelemetry.sdk.metrics.export import (
    ExportRecord,
    MetricsExporter,
    MetricsExportResult,
)
from opentelemetry.sdk.metrics.export.aggregate import (
    Aggregator,
    LastValueAggregator,
    MinMaxSumCountAggregator,
    SumAggregator,
)

from dogstatsd_metric_exporter import configuration, errors, queue
from dogstatsd_metric_exporter.types import (
    NUMBER_TYPES,
    T_BATCH,
    T_NUMBER,
    T_PACKET,
    T_TAGS,
)

logger = logging.getLogger(__name__)


FORMAT_COUNTER = "c"
FORMAT_HISTOGRAM = "h"
FORMAT_GAUGE = "g"
FORMAT_TIMING = "ms"

E_RECORD_TOO_LONG = (
    "Line is exceeding max packet size, %(length)d out of %(max_length)d characters"
)
E_FAILED_SEND_PACKET = "Failed to send packet"


class DogStatsDMetricsExporter(MetricsExporter):
    # Note:
    #   Are currently not handled:
    #       - MinMaxSumCountAggregator
    #       - ValueObserverAggregator

    def __init__(
        self, cfg: configuration.Configuration,
    ):
        self._client = base.DogStatsd(
            socket_path=cfg.uds_path, namespace=cfg.prefix, **cfg.additional,
        )

        self.max_packet_length: int = cfg.max_packet_length

        self.include_resource_attributes: bool = cfg.include_resource_attributes
        self.fail_silently = cfg.fail_silently

        # FIFO queue of batches
        self._queue = queue.Queue(
            batch_count_limit=cfg.maximum_buffer_batch_count,
            fail_silently=self.fail_silently,
            send_packet=self.send_packet,
        )

    def format_tags_from_record(self, record: ExportRecord) -> T_TAGS:
        """Format a OpenTelemetry record labels into DogStatsD tag format.

        - Takes a n-tuple of 2-tuple strings (key-pair): ``(("K", "V"), ...)``
        - Puts them into a statsd n-tuple of a single string tag: ``("K:V", ...)``
        """
        labels = record.labels

        if self.include_resource_attributes is True:
            attributes: ItemsView = record.resource.attributes.items()
            labels = tuple(attributes) + labels

        return tuple(f"{k}:{v}" for [k, v] in labels)

    def format_single_stat(
        self, *, record: ExportRecord, value: T_NUMBER, fmt: str, tags: T_TAGS
    ) -> str:
        client = self._client
        payload = client._serialize_metric(
            metric=record.instrument.name, value=value, metric_type=fmt, tags=tags,
        )
        return f"{payload}\n"

    def format_record(self, record: ExportRecord) -> str:
        aggregator: Aggregator = record.aggregator
        aggregator_type = type(aggregator)

        tags = self.format_tags_from_record(record)
        value: T_NUMBER = aggregator.checkpoint

        if aggregator_type is SumAggregator:
            fmt = FORMAT_COUNTER
        elif aggregator_type is LastValueAggregator:
            fmt = FORMAT_GAUGE
        elif aggregator_type is MinMaxSumCountAggregator:
            value = aggregator.checkpoint.sum
            fmt = FORMAT_GAUGE
        else:
            raise errors.UnsupportedAggregator(aggregator_type)

        if isinstance(value, NUMBER_TYPES) is False:
            raise errors.UnsupportedValueType(type(value))

        return self.format_single_stat(record=record, value=value, fmt=fmt, tags=tags)

    def format_records(
        self, records: Sequence[ExportRecord]
    ) -> Generator[T_PACKET, None, None]:
        lines: list[str] = []
        current_length = 0

        for record in records:
            try:
                line = self.format_record(record)
            except errors.BaseDogStatsDException as exc:
                if self.fail_silently is False:
                    raise

                logger.error(exc.message, exc_info=exc)
                continue

            # Drop record if the record is too long to be safely sent
            if len(line) > self.max_packet_length:
                if self.fail_silently is False:
                    raise errors.TooLongRecord(line, self.max_packet_length)
                logger.error(
                    E_RECORD_TOO_LONG,
                    {"length": len(line), "max_length": self.max_packet_length},
                    exc_info=True,
                )
                continue

            current_length += len(line)

            # If the last processed record is not fitting
            # yield the previous records and keep the current record as to be sent
            # into another packet
            if current_length > self.max_packet_length:
                yield "".join(lines)
                lines = []
                current_length = len(line)

            lines.append(line)

        # Return the leftovers to be sent in a packet
        yield "".join(lines)

    def send_packet(self, packet: str) -> None:
        packets_sent = 1
        bytes_sent = len(packet)

        if self._client._xmit_packet(packet, True) is False:
            raise RuntimeError(E_FAILED_SEND_PACKET)

        logger.debug("Sent %d packets (%d bytes)", packets_sent, bytes_sent)

    def flush_buffer(self) -> MetricsExportResult:
        return self._queue.maybe_flush()

    def append_to_buffer(self, records: T_BATCH) -> None:
        self._queue.append(records)

    def export(self, export_records: Sequence[ExportRecord]) -> MetricsExportResult:
        logger.debug("Received %d records", len(export_records))
        self.flush_buffer()

        if export_records:
            packets = list(self.format_records(export_records))
            self.append_to_buffer(packets)
            return self.flush_buffer()
        return MetricsExportResult.SUCCESS

    def shutdown(self) -> None:
        """
        On shutdown, we no longer attempt to flush the metrics.

        ``PushController`` will have already invoked ``export`` which will
        attempt to flush the buffer.

        Reference: https://github.com/open-telemetry/opentelemetry-python/pull/749
        """
