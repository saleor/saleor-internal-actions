import logging
import os
from datetime import datetime
from time import sleep
from typing import Optional, List, Tuple

import pytz
import requests
from django.core.management import base

from tenants.limits.collector import TenantMetricManager, trace

logger = logging.getLogger(__name__)


class TemporaryFailure(Exception):
    def __init__(self, message: str, details: dict):
        self.message = message
        self.details = details
        super().__init__(message, details)

    def __str__(self) -> str:
        return f"{self.message}: {self.details}"


def maybe_raise_for_status(status_code: int, expected_code: int):
    # Allow to retry on HTTP 500 due to API Gateway returning 500 when timing out
    # e.g. development deployment is scaled to 0 at the time of the request
    if status_code >= 500:
        raise TemporaryFailure(
            "Got a temporary error from server",
            {"status_code": status_code},
        )

    # Raise permanent error for any other failure
    if status_code != expected_code:
        raise requests.HTTPError(
            "Received an unexpected status code",
            {"status_code": status_code, "expected_code": expected_code},
        )


class PayloadSender:
    __slots__ = (
        "endpoint",
        "timeout",
        "max_retries",
        "retry_delay",
        "secret_authorization_header",
    )

    def __init__(
        self,
        *,
        endpoint: str,
        timeout: int,
        max_retries: int,
        retry_delay: int,
        http_secret_authorization: str,
    ):
        """
        Params
            endpoint: the full URL to the service where to send the data via PUT
            max_retries: maximum retry count
            retry_delay: the duration to wait between each attempt
            http_secret_authorization: the authorization header value, e.g. "Token XXX"
        """
        self.endpoint = endpoint
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.secret_authorization_header = http_secret_authorization

    @trace
    def _send(self, payload: dict) -> List[str]:
        """
        Raises TemporaryFailure if status code is higher than 500 or timeout occurred.
        """
        try:
            response = requests.put(
                self.endpoint,
                json=payload,
                timeout=self.timeout,
                headers={"Authorization": self.secret_authorization_header},
            )
        except requests.Timeout as exc:
            raise TemporaryFailure("Timed out", {}) from exc

        # Raise temporary failure if >500, raise permanent if not 200
        maybe_raise_for_status(response.status_code, expected_code=200)

        # Check the response for any errors
        data = response.json()
        return data["errors"]

    def retry(self, payload: dict, *, attempt: int, exc_info):
        logger.exception(
            (
                "Temporary failure for sending tenants usage metrics, "
                "will retry after %d seconds: %s"
            ),
            self.retry_delay,
            exc_info,
            exc_info=exc_info,
        )
        sleep(self.retry_delay)
        return self.send_or_retry(payload, attempt=attempt + 1)

    def send_or_retry(self, payload: dict, *, attempt: int = 1) -> List[str]:
        try:
            return self._send(payload)
        except TemporaryFailure as exc:
            if attempt >= self.max_retries:
                raise RuntimeError("Exhausted maximum attempt count") from exc
            return self.retry(payload, attempt=attempt, exc_info=exc)


class Command(base.BaseCommand):
    def add_arguments(self, parser: base.CommandParser) -> None:
        group = parser.add_argument_group(
            "Metric Collector Command",
            description=(
                "Command sends current usage of all tenants to Cloud API"
                "and expects to receive endpoint that might look like this: "
                "http[s]://cloud-api.<NAMESPACE>.svc.cluster.local"
                "service/usage/environments/"
            ),
        )
        group.add_argument(
            "--timeout",
            type=int,
            help="The maximum wait time to send payload until raising time out",
            default=60,
        )
        group.add_argument(
            "--retries",
            type=int,
            help="The maximum retry count for sending payload",
            required=True,
        )
        group.add_argument(
            "--retry-delay",
            type=int,
            help=(
                "The delay for attempting a resend of the usages payload "
                "after temporary send failure"
            ),
            required=True,
        )
        group.add_argument(
            "--endpoint",
            type=str,
            required=True,
            help="Service endpoint to send the data as PUT",
        )

    @staticmethod
    @trace
    def collect_tenants_usage_metrics_task() -> Tuple[dict, int]:
        manager = TenantMetricManager()
        manager.collect_metrics()
        collected_at: str = datetime.now().replace(tzinfo=pytz.UTC).isoformat()
        records = manager.as_list()
        payload = {"usages": records, "collected_at": collected_at}
        return payload, len(records)

    @staticmethod
    def get_secret_authorization_header() -> str:
        """
        Return whether token authentication or any arbitrary authorization value.

        Returns "Token <token value>" if ``SERVICE_TOKEN`` is provided.
        Otherwise, "<arbitrary method> <token value>" from ``SERVICE_AUTHORIZATION_VALUE``

        Raises:
            * KeyError: when did not find any HTTP credentials
            * ValueError: when received an invalid HTTP authorization value
        """
        secret_token: Optional[str] = os.environ.get("SERVICE_TOKEN")
        if secret_token is not None:
            return f"Token {secret_token}"
        # e.g. "JWT xxx", "FOO xxx"
        secret_authorization_value = os.environ["SERVICE_AUTHORIZATION_VALUE"]
        if secret_authorization_value.find(" ") == -1:
            raise ValueError(
                "SERVICE_AUTHORIZATION_VALUE is expected to be: "
                "'<AUTH_METH> <credential value>'"
            )
        return secret_authorization_value

    def handle(
        self,
        *args,
        timeout: int,
        retries: int,
        retry_delay: int,
        endpoint: str,
        **_options,
    ):
        secret_auth: str = self.get_secret_authorization_header()
        payload, record_count = self.collect_tenants_usage_metrics_task()
        sender = PayloadSender(
            timeout=timeout,
            max_retries=retries,
            retry_delay=retry_delay,
            endpoint=endpoint,
            http_secret_authorization=secret_auth,
        )
        errors = sender.send_or_retry(payload)
        if len(errors) == 0:
            logger.info(
                "Target successfully received and handled %d records", record_count
            )
        else:
            logger.warning(
                "Target successfully received %d records but returned %d errors: %r",
                record_count,
                len(errors),
                errors,
            )
