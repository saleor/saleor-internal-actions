Contributing
============

.. contents::


DogStatsD Client
################

The used StatsD client is the official DataDog's base `dogstatsd.base.DogStatsd <DogStatsDDocs_>`_ for Python.

The only logics used from the base client is the UDP connection handling, the string formatting and escaping.

Readings
^^^^^^^^

* | DogStatsD Client for Python:
  | https://datadogpy.readthedocs.io/en/latest/#datadog.dogstatsd.base.DogStatsd

* | Metrics and Examples:
  | https://docs.datadoghq.com/developers/metrics/dogstatsd_metrics_submission/

* | Dog's StatsD Mapper and Query Syntax:
  | https://www.datadoghq.com/blog/dogstatsd-mapper/#how-dogstatsd-mapper-works

.. _DogStatsDDocs: https://datadogpy.readthedocs.io/en/latest/#datadog.dogstatsd.base.DogStatsd


Metric Exporter
===============

The DogStatsD exporter for OpenTelemetry is based on OpenTelemetry's Go implementation:
https://github.com/open-telemetry/opentelemetry-go-contrib/tree/v0.16.0/exporters/metric/dogstatsd.

But our implementation differs in many ways:

* The client:

  * UDP connection handling to StatsD and logics are leveraged to DataDog's Python Library
  * Sanitizations are also leveraged to DataDog's library


Meter Provider
==============

The meter provider *should* be non-stateful in order to leverage incrementing to the StatsD server.
In stateful mode, the counter will not act as an increment and thus will set the value wrongly.

.. [#MapSumAggregator] Mapping for ``SumAggregator`` in 0.17.x
  https://github.com/open-telemetry/opentelemetry-python/blob/v0.17b0/opentelemetry-sdk/src/opentelemetry/sdk/metrics/view.py#L177-L178
