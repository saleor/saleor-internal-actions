from django.conf import settings
from opentelemetry import metrics
from opentelemetry.sdk.metrics import MeterProvider

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
provider = MeterProvider(stateful=False)
metrics.set_meter_provider(provider)

# Retrieve the meter (returns a Meter object and not MeterProvider)
meter = provider.get_meter(__name__)

if settings.OPTL_ENABLED is True:
    # Create a push controller for the metrics to be exported to DogStatsD
    #
    # ``start_pipeline`` must be called directly otherwise the exporter and controller
    # will not get shutdown gracefully. Ref: https://git.io/JmhqW
    provider.start_pipeline(meter, exporter, INTERVAL)
