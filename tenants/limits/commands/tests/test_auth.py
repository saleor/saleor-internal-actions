from unittest import mock

import pytest
from django.core.management import call_command

from . import conftest as t


@pytest.mark.parametrize(
    "environ_key, value, expected_authorization_value",
    [
        # Authorization: token <value>
        ("SERVICE_TOKEN", "my_service_token", "Token my_service_token"),
        # Authorization: jwt <value>
        ("SERVICE_AUTHORIZATION_VALUE", "jwt my_key", "jwt my_key"),
    ],
)
def test_jwt_authentication(
    tenant_connection_keeper,
    environ,
    fake_put_records,
    environ_key,
    value,
    expected_authorization_value,
):
    environ[environ_key] = value

    fake_response = t.mk_fake_response(status=200, content={"errors": []})
    fake_put_records.return_value = fake_response

    call_command("collect_metrics", *t.VALID_CMD_OPTS)

    # Should only call once
    assert fake_put_records.call_count == 1, fake_put_records.call_args_list

    # Should have sent authorization header
    call: mock.call = fake_put_records.call_args
    headers: dict = call.kwargs["headers"]
    assert headers.get("Authorization") == expected_authorization_value


def test_raises_missing_credentials(tenant_connection_keeper, fake_put_records):
    """Missing credential must raise KeyError"""
    with pytest.raises(KeyError) as exc:
        call_command("collect_metrics", *t.VALID_CMD_OPTS)
    assert exc.value.args == ("SERVICE_AUTHORIZATION_VALUE",)
    fake_put_records.assert_not_called()


def test_raises_invalid_custom_authorization_value(
    tenant_connection_keeper, fake_put_records, environ
):
    """
    Should raise when the authorization header only contains a key
    but not the authentication method.

    Expects to receive ``<auth_meth> <value>``
    """
    environ["SERVICE_AUTHORIZATION_VALUE"] = "my_token"

    with pytest.raises(ValueError) as exc:
        call_command("collect_metrics", *t.VALID_CMD_OPTS)
    assert exc.value.args == (
        "SERVICE_AUTHORIZATION_VALUE is expected to be: '<AUTH_METH> <credential value>'",
    )
    fake_put_records.assert_not_called()
