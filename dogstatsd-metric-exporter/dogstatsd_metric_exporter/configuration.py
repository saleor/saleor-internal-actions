import dataclasses
from typing import Optional

from datadog.dogstatsd import base

DEFAULT_MAX_PACKET_LENGTH = base.UDS_OPTIMAL_PAYLOAD_LENGTH


@dataclasses.dataclass(frozen=True)
class Configuration:
    # Unix Domain Socket path
    uds_path: Optional[str]

    # Prefix for all metric names
    # Example: ``prefix = "abc"`` => ``abc.metric``
    prefix: Optional[str] = None

    # Whether the resource attributes associated to the meter provider
    # should be included in the tags
    #
    # Be aware that enabling the flag could cause high cardinality,
    # meaning billed custom metrics could be:
    #   \[ \sum_{metric=1}^{\infty} metric = 1 * labels * attributes \]
    #
    # Disabled by default
    include_resource_attributes: bool = False

    # The maximum optimal packet length for a UDS packet
    # Default is the known value that works well against all Cloud providers
    max_packet_length: int = DEFAULT_MAX_PACKET_LENGTH

    # The maximum of batches to hold in the buffer
    # They contain a packet list of each export.
    # In case of send failure, it will retry later.
    #
    # If the buffer value has more than the given maximum count,
    # the oldest batch is dropped
    maximum_buffer_batch_count = 10

    # Whether errors should be raised or not
    # Value should be ``False`` for development ONLY, and always ``True`` for production
    #
    # If ``False`` in production, any exception will cause the exporter to die
    # and won't restart until restarting the deployment
    fail_silently: bool = True

    # Additional settings for ``datadog.dogstatsd.base.DogStatsd.__init__``
    additional: dict = dataclasses.field(default_factory=dict)
