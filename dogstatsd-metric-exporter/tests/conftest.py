import unittest.mock
from typing import Any, Callable, Optional

import pytest
from opentelemetry import metrics
from opentelemetry.metrics import Counter, Meter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import ExportRecord, aggregate
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.util import get_dict_as_key
from opentelemetry.util.types import AttributesAsKey

from dogstatsd_metric_exporter import DogStatsDMetricsExporter, configuration

from .utilities.log_mock import LoggingPatcher


@pytest.fixture
def resource_labels() -> dict[str, Any]:
    return {
        "key_with_str_value": "Some String",
        "key_with_int_value": 123,
        "key_with_boolean": True,
    }


@pytest.fixture
def labels() -> AttributesAsKey:
    return get_dict_as_key({"environment": "staging", "build_id": 512})


@pytest.fixture
def meter(resource_labels) -> Meter:
    metrics.set_meter_provider(MeterProvider(resource=Resource(resource_labels)))
    meter = metrics.get_meter(__name__)
    return meter


@pytest.fixture
def resource() -> Resource:
    return metrics.get_meter_provider().resource


@pytest.fixture
def dummy_metric() -> Counter:
    meter = metrics.get_meter(__name__)
    metric = meter.create_counter("dummy", "dummy description", "1", int)
    return metric


@pytest.fixture
def dummy_aggregator() -> aggregate.SumAggregator:
    aggregator = aggregate.SumAggregator()
    aggregator.update(2)
    aggregator.take_checkpoint()
    return aggregator


@pytest.fixture
def dummy_record(dummy_metric, dummy_aggregator, resource) -> ExportRecord:
    return ExportRecord(dummy_metric, tuple(), dummy_aggregator, resource)


@pytest.fixture
def unsupported_record(resource) -> ExportRecord:
    """Return a record of a unsupported aggregator"""
    meter = metrics.get_meter(__name__)
    metric = meter.create_counter("unsupported", "description", "1", int)

    aggregator = aggregate.HistogramAggregator()
    aggregator.update(1)
    aggregator.take_checkpoint()

    record = ExportRecord(metric, tuple(), aggregator, resource)
    return record


@pytest.fixture
def exporter() -> DogStatsDMetricsExporter:
    return DogStatsDMetricsExporter(
        cfg=configuration.Configuration(
            include_resource_attributes=False, fail_silently=False, uds_path=None,
        ),
    )


@pytest.fixture
def mocked_xmit_packet(exporter) -> unittest.mock.MagicMock:
    """Mocks ``datadog.dogstatsd.base.DogStatsd._xmit_packet``"""
    with unittest.mock.patch.object(exporter._client, "_xmit_packet") as mocked:
        yield mocked


@pytest.fixture
def mock_flush(exporter) -> Callable[[Any], unittest.mock.MagicMock]:
    class _MockFlush:
        def __init__(self):
            self.mock: Optional[unittest.mock.MagicMock] = None

        def start(self, wraps: Any) -> unittest.mock.MagicMock:
            if wraps is True:
                wraps = exporter.flush_buffer
            mock = unittest.mock.patch.object(exporter, "flush_buffer", wraps=wraps)
            self.mock = mock
            return mock.start()

        def stop(self):
            if self.mock is not None:
                self.mock.stop()

    manager = _MockFlush()
    yield manager.start
    manager.stop()


@pytest.fixture
def log_patcher() -> LoggingPatcher:
    """
    Usage:
        >>> import logging
        >>>
        >>> my_logger = logging.getLogger("my_app.my_logger")
        >>> my_logger.setLevel(logging.INFO)
        >>>
        >>>
        >>> def dummy_logging():
        ...     my_logger.info("Hello %(name)s!", name="John Wick")
        >>>
        >>>
        >>> def test_my_logging(log_patcher):
        ...     # ``messages`` will contain the intercepted messages
        ...     with log_patcher.init(my_logger) as messages:
        ...         # Invoke code using ``my_logger``
        ...         dummy_logging()
        ...
        ...     assert "INFO" in len(messages)
        ...     record: logging.LogRecord = assert messages["INFO"][0]
        ...     assert record.message == "Hello"
        ...     assert record.args == {"name": "John Wick"}
    """
    patcher = LoggingPatcher()

    yield patcher

    if patcher.is_active is True:
        patcher.stop()
