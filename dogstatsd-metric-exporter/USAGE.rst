Usage
=====

.. contents:: Contents


Configuration
#############

The ``DogStatsDMetricsExporter`` takes a ``Configuration`` object
from its module that has for options:

.. table::

  +---------------------------------+------------+
  | Field                           | Type       |
  +=================================+============+
  | ``uds_path``                    | string     |
  +---------------------------------+------------+
  | ``prefix``                      | string     |
  +---------------------------------+------------+
  | ``include_resource_attributes`` | boolean    |
  +---------------------------------+------------+
  | ``max_packet_length``           | integer    |
  +---------------------------------+------------+
  | ``maximum_buffer_batch_count``  | integer    |
  +---------------------------------+------------+
  | ``fail_silently``               | boolean    |
  +---------------------------------+------------+
  | ``additional``                  | dictionary |
  +---------------------------------+------------+

For default values, refer to `dogstatsd_metric_exporter/configuration.py <dogstatsd_metric_exporter/configuration.py>`_.


Maximum Packet Length
^^^^^^^^^^^^^^^^^^^^^

The default maximum packet length is set to the size in bytes that is known
to work reliably enough over most Cloud providers.


Fail Silently Option (Danger)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

When developing metrics and/or DogStatsD exporter, it is useful to set the value to ``False``
in order to instantly see exceptions rather than waiting for logs to come in.

In production it shall always be set to ``True``, i.e. always fail silently.
If a failure happens, such as network error or unsupported metric, the exporter
will skip the failed record, log the error and continue to processing.

If set to ``False``, it will abort and raise the exception killing itself
and will no longer process any metric until the deployment is restarted.


Maximum Batch Count in Buffer
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

A maximum number of batches will be kept in memory if there is a failure,
such as a temporary network failure.

A batch is defined as a list of packets containing metrics
that were supplied by OpenTelemetry's ``PushController`` to be exported
(``DogStatsDMetricsExporter.export``).

A packet is a list of DogStatsD metric queries such as "for metric foo, increment by 10",
they are from ``1..N`` packets. If ``N>1`` all ``N - 1`` packets
are around the size of ``max_packet_length`` (8192 bytes).

If we assume that all metrics, with all labels/attributes can fit in a single packet,
then the maximum size of a buffer would be:

.. math::

  \begin{equation} \label{eq1}
  \begin{split}
  MaxBufferSize & = MaxPacketLength * MaxBufferBatchCount \\
                & = 8192 * 10 \\
                & = 81,920 \\
                & = 81.92\ \text{KiB}
  \end{split}
  \end{equation}


UDS Path and UDP Option
^^^^^^^^^^^^^^^^^^^^^^^

When ``uds_path`` is not set, it will default to UDP ``localhost:8125`` which can be
overridden through settings additional options, such as:

.. code-block:: python

  Configuration(
      max_packet_length=1432,
      additional={"port": 8125, "host": "127.0.0.1"},
  )


For more additional options, refer to https://datadogpy.readthedocs.io/en/latest/#datadog.dogstatsd.base.DogStatsd.

.. warning::

  Always set the maximum packet length to 1432 by default for UDP if production.
  But UDP is not recommended in production due to lack of dropped packets reporting.


Integrating to OpenTelemetry
############################

To connect the exporter to OpenTelemetry, a ``PushController`` must be created
and associated to the DogStatsD exporter.

Important Notes
^^^^^^^^^^^^^^^

.. danger::

  Always disable the stateful mode of the OpenTelemetry meter provider:

  .. code-block:: python

    provider = MeterProvider(stateful=False)

  StatsD is instructed through increment procedures rather than the sum of the metric.

  Assuming the export interval is 10 seconds,
  and the metric ``foo`` gets incremented by 10 over 10 seconds;
  and during the whole application's lifetime the sum of ``foo`` is 1000:

  When the stateful mode is:

  - Disabled, every 10 seconds it would sends to StatsD: "for metric 'foo', increment by 10"
  - Enabled, every 10 seconds it would sends to StatsD: "for metric 'foo', increment by 1000" -
    where 1000 keeps on getting incremented by 10.


Full Code Example
#################

.. code-block:: python

  from opentelemetry import metrics
  from opentelemetry.sdk.metrics import MeterProvider, PushController
  from opentelemetry.sdk.resources import Resource

  from dogstatsd_metric_exporter import Configuration, DogStatsDMetricsExporter

  # The collect/export interval in seconds
  INTERVAL: float = 10

  # The DogStatsD metric exporter - Can take UDS path or UDP host and port
  exporter = DogStatsDMetricsExporter(
      Configuration(prefix="nonstat", uds_path="/var/run/datadog/dsd.socket")
  )

  # Set the meter provider to default provider
  # Resource parameter can be omitted, resource can take global attributes/labels
  metrics.set_meter_provider(MeterProvider(stateful=False, resource=Resource({})))

  # Retrieve the meter (returns a Meter object and not MeterProvider)
  meter = metrics.get_meter(__name__)

  # Create a push controller for the metrics to be exported to DogStatsD
  controller = PushController(meter, exporter, INTERVAL)
