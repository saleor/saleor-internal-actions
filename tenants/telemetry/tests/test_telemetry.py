from typing import List
from unittest import mock

import pytest

from opentelemetry.sdk.metrics import PushController

from .. import provider


@pytest.fixture
def wrapped_exporter_shutdown() -> mock.MagicMock:
    exporter = provider.exporter
    with mock.patch.object(exporter, "shutdown", wraps=exporter.shutdown) as mocked:
        yield mocked


@pytest.fixture
def wrapped_exporter_flush() -> mock.MagicMock:
    exporter = provider.exporter
    with mock.patch.object(
        exporter, "flush_buffer", wraps=exporter.flush_buffer
    ) as mocked:
        yield mocked


@pytest.fixture
def wrapped_exporter_export() -> mock.MagicMock:
    exporter = provider.exporter
    with mock.patch.object(exporter, "export", wraps=exporter.export) as mocked:
        yield mocked


@pytest.fixture
def exporter(
    client, wrapped_exporter_shutdown, wrapped_exporter_flush, wrapped_exporter_export
):
    """Mock the global DogStatsD exporter"""
    return provider.exporter


@pytest.fixture
def mocked_push_controller_shutdown():
    """Protect the push controller to stop it from shutting down its thread"""
    push_controllers: List[PushController] = provider.provider._controllers
    assert len(push_controllers) == 1, "unexpected controller count"

    # Disable the shutdown method
    with mock.patch.object(push_controllers[0], "shutdown") as mocked_shutdown:
        yield mocked_shutdown


def test_graceful_shutdown(mocked_push_controller_shutdown, exporter):
    """
    Call stack:
        MeterProvider.shutdown()
            -> PushController.shutdown() [blocked via mock]
                -> tick()
                    -> exporter.export() [DogStatsD]
                -> stop thread
            -> exporter.shutdown() [DogStatsD]
            -> unregister_aexit()
    """
    mocked_push_controller_shutdown.assert_not_called()
    exporter.export.assert_not_called()
    exporter.shutdown.assert_not_called()
    exporter.flush_buffer.assert_not_called()

    # Shutdown
    provider.provider.shutdown()

    # Ensure the push controller got requested to shutdown
    # Its job is to collect the metrics before shutting down and exporting them
    mocked_push_controller_shutdown.assert_called_once()

    # Once the push controller is done (blocking),
    # the dogstatsd exporter will flush its buffer a final time
    exporter.export.assert_not_called()  # tick() should have been blocked
    exporter.shutdown.assert_called_once()  # MeterProvider should have called shutdown
    exporter.flush_buffer.assert_called_once()  # self.shutdown() => self.flush()
