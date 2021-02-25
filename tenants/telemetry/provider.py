from django.conf import settings
from opentelemetry import metrics
from opentelemetry.sdk.metrics import MeterProvider, PushController

from dogstatsd_metric_exporter import Configuration, DogStatsDMetricsExporter

# The collect/export interval in seconds
INTERVAL: float = settings.OPTL_METRIC_EXPORT_INTERVAL

# DogStatsD metric exporter can take UDS path or UDP host and port
exporter = DogStatsDMetricsExporter(
    Configuration(prefix=settings.OPTL_NAMESPACE, uds_path=settings.OPTL_UDS_PATH)
)

# Set the meter provider to default provider
# DANGERS: (refer to dogstatsd_metric_exporter's USAGE.rst for explanations)
# * DO NOT set stateful to true if using DogStatsD, it is not supported
# * Think twice before setting resource attributes/labels, it increases cardinality
#   thus pricing.
metrics.set_meter_provider(MeterProvider(stateful=False))

# Retrieve the meter (returns a Meter object and not MeterProvider)
meter = metrics.get_meter(__name__)

# Create a push controller for the metrics to be exported to DogStatsD
controller = PushController(meter, exporter, INTERVAL)
