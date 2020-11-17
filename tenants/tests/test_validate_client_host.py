import mock
from tenants.utils import validate_client_host


@mock.patch("tenants.utils.connection.tenant.domain_url", "example.com")
@mock.patch("tenants.utils.connection.tenant.allowed_client_origins", [])
def test_validate_same_origin_client_host():
    assert validate_client_host("example.com")
    assert not validate_client_host("test-example.com")
    assert not validate_client_host("testexample.com")


@mock.patch("tenants.utils.connection.tenant.domain_url", "example.saleor.cloud")
@mock.patch("tenants.utils.connection.tenant.allowed_client_origins", [])
def test_validate_cloud_same_origin_client_host():
    assert validate_client_host("example.saleor.cloud")
    assert validate_client_host("test-example.saleor.cloud")
    assert not validate_client_host("testexample.saleor.cloud")


@mock.patch("tenants.utils.connection.tenant.domain_url", "example.com")
@mock.patch("tenants.utils.connection.tenant.allowed_client_origins", ["*"])
def test_validate_any_client_host():
    assert validate_client_host("example.com")
    assert validate_client_host("domain.com")
    assert validate_client_host("other-domain.com")


@mock.patch("tenants.utils.connection.tenant.domain_url", "example.com")
@mock.patch(
    "tenants.utils.connection.tenant.allowed_client_origins",
    ["http://localhost:3000", "http://domain.com"],
)
def test_validate_custom_client_hosts():
    assert validate_client_host("localhost")
    assert validate_client_host("example.com")
    assert validate_client_host("domain.com")
    assert not validate_client_host("other-domain.com")
