import json
from typing import Dict, Tuple, Union
from unittest import mock
from urllib.parse import urljoin

import pytest
from requests import Response

from tenants.tests.fixtures import API_SVC_TEST_API_ENDPOINT

# TODO: remove those
SUCCESS_RESPONSE = {"errors": []}
PARTIAL_SUCCESS_RESPONSE = {"errors": ["Oops something went wrong somewhere"]}

SVC_ENDPOINT = urljoin(API_SVC_TEST_API_ENDPOINT, "usage/environments/")

VCR_CONFIG = dict(
    record_mode="once",
    filter_headers=("User-Agent",),
)

MAX_RETRIES = 4
RETRY_DELAY = 3


def unpack_args(args: Dict[str, str]) -> Tuple[str, ...]:
    unpacked = ()
    for group in args.items():
        unpacked += group
    return unpacked


VALID_CMD_OPTS_PACKED: Dict[str, str] = {
    "--timeout": "1",
    "--retries": str(MAX_RETRIES),
    "--retry-delay": str(RETRY_DELAY),
    "--endpoint": SVC_ENDPOINT,
}

VALID_CMD_OPTS = unpack_args(VALID_CMD_OPTS_PACKED)

VALID_PUT_REQUEST_PAYLOAD = {
    "collected_at": "2019-03-15T07:30:33.511276+00:00",
    "usages": [
        {
            "channels": 0,
            "host": "mirumee.com",
            "orders": 0,
            "project_id": 23,
            "staff_users": 0,
            "variants": 0,
            "warehouses": 0,
        },
        {
            "channels": 0,
            "host": "othertenant.com",
            "orders": 0,
            "project_id": 54,
            "staff_users": 0,
            "variants": 0,
            "warehouses": 0,
        },
    ],
}

DEFAULT_ENDPOINT_CALL = mock.call(
    SVC_ENDPOINT,
    json=VALID_PUT_REQUEST_PAYLOAD,
    timeout=1,
    headers={"Authorization": "Token fake_value_xxx"},
)


@pytest.fixture
def fake_auth(environ):
    environ.setdefault("SERVICE_TOKEN", "fake_value_xxx")


@pytest.fixture
def fake_put_records():
    reference = "tenants.limits.commands.collect_metrics.requests.put"
    with mock.patch(reference) as mocked:
        yield mocked


@pytest.fixture
def fake_sleep():
    reference = "tenants.limits.commands.collect_metrics.sleep"
    with mock.patch(reference) as mocked:
        yield mocked


def mk_fake_response(*, status: int, content: Union[bytes, dict] = b"") -> Response:
    if isinstance(content, bytes) is False:
        cleaned_content: bytes = json.dumps(content).encode()
    else:
        cleaned_content: bytes = content

    response = Response()
    response.status_code = status
    response._content = cleaned_content
    return response
