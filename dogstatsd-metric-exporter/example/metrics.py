import logging
import socket
from os import getenv

from opentelemetry import metrics
from opentelemetry.sdk.metrics import MeterProvider, PushController
from opentelemetry.sdk.resources import Resource

from dogstatsd_metric_exporter import Configuration, DogStatsDMetricsExporter

# - name: POD_UID
#   valueFrom:
#     fieldRef:
#       fieldPath: metadata.uid
hostname = getenv("POD_UID")
if hostname is None:
    hostname = socket.gethostname()

logging.basicConfig(level=logging.DEBUG)

exporter = DogStatsDMetricsExporter(
    Configuration(prefix="nonstat", uds_path="/var/run/datadog/dsd.socket")
)

metrics.set_meter_provider(MeterProvider(stateful=False, resource=Resource({})))
meter = metrics.get_meter(__name__)
controller = PushController(meter, exporter, 5)

requests_counter = meter.create_counter(
    name="requests", description="number of requests", unit="1", value_type=int,
)

request_body_length = meter.create_valuerecorder(
    name="request_body_length", description="", unit="By", value_type=int
)
response_body_length = meter.create_valuerecorder(
    name="response_body_length", description="", unit="By", value_type=int
)
