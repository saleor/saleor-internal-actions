import pytest

from tenants.middleware import SaleorTenantMiddleware


@pytest.mark.parametrize(
    "hostname,expected_tenant_domain",
    [
        ("client.test.local", "client.test.local"),
        ("client.test.local-1", "client.test.local-1"),
        ("client.test-beta.local", "client.test-beta.local"),
        ("-client.test.local", "client.test.local"),
        ("prod-client.test.local", "client.test.local"),
        ("prod--client.test.local", "client.test.local"),
        ("test-prod-client.test.local", "client.test.local"),
    ],
)
def test_hostname_handling(hostname, expected_tenant_domain):
    assert (
        SaleorTenantMiddleware().get_base_domain_url(hostname) == expected_tenant_domain
    )
