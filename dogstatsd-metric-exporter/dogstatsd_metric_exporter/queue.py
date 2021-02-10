import logging
from typing import Callable

from opentelemetry.sdk.metrics.export import MetricsExportResult

from dogstatsd_metric_exporter.types import T_BATCH, T_PACKET

logger = logging.getLogger(__name__)

W_TOO_MANY_BATCHES = "Too many batches in queue, dropping the oldest"


class Queue:
    __slots__ = ["_buffer", "batch_count_limit", "fail_silently", "send_packet"]

    def __init__(
        self,
        *,
        batch_count_limit: int,
        fail_silently: bool,
        send_packet: Callable[[str], None],
    ):
        # Buffer contains the list of batches containing a list of packets
        # The buffer is FIFO
        self._buffer: list[T_BATCH] = []

        # Limit of batches to hold into the buffer
        self.batch_count_limit = batch_count_limit

        # If true (production), any exception will be silent
        # and communicated to the logger
        self.fail_silently = fail_silently

        # The function or method to invoke in order to send the packet
        self.send_packet = send_packet

    def append(self, records: T_BATCH) -> None:
        """
        Appends an export batch of packets into the queue buffer
        """

        self._buffer.append(records)

        # Drop oldest packet if buffer is full
        if len(self._buffer) > self.batch_count_limit:
            logger.warning(W_TOO_MANY_BATCHES)
            del self._buffer[0]

    def _must_flush_batch(self, batch: T_BATCH) -> None:
        packet_count = len(batch)
        i = packet_count - 1

        logger.info("Flushing %d packets", packet_count)

        while i >= 0:
            packet: T_PACKET = batch[i]
            self.send_packet(packet)
            del batch[i]
            i -= 1

    def _must_maybe_flush(self) -> None:
        """
        Flush the buffer using a FIFO order if not empty.
        """

        if not self._buffer:
            logger.debug("Empty buffer, skipping")
            return

        batch_size = len(self._buffer)
        i = batch_size - 1

        logger.info("Flushing %d batches", batch_size)

        while i >= 0:
            batch = self._buffer[i]

            # Skip empty batch
            if len(batch) > 0:
                self._must_flush_batch(batch)

            del self._buffer[i]
            i -= 1

    def maybe_flush(self) -> MetricsExportResult:
        """
        Flush without raising exception if set to fail silently.
        Returns whether it is a success or not.
        """
        try:
            self._must_maybe_flush()
        except Exception as exc:
            if self.fail_silently is False:
                raise
            logger.exception("Failed to flush the buffer", exc_info=exc)
            return MetricsExportResult.FAILURE
        return MetricsExportResult.SUCCESS
