from django.contrib.sites.models import Site
from django.core.management import call_command
from tenant_schemas.utils import tenant_context

from tenants.limits.models import TenantLimitsMixin
from tenants.management.commands.tests.conftest import get_limits_fields
from tenants.models import Tenant

CMD = "updatetenant"


def test_update_tenant_domain(test_tenant):
    call_command(CMD, "--new-domain", "new_domain")

    test_tenant.refresh_from_db(fields=["domain_url"])
    assert test_tenant.domain_url == "new_domain"
    with tenant_context(test_tenant):
        site = Site.objects.get()
        assert site.domain == "new_domain"


def test_update_tenant_which_changed_site_domain(test_tenant):
    with tenant_context(test_tenant):
        site = Site.objects.get()
        site.domain = "updated_domain"
        site.save()

    call_command(CMD, "--new-domain", "new_domain")

    test_tenant.refresh_from_db(fields=["domain_url"])
    assert test_tenant.domain_url == "new_domain"
    site.refresh_from_db(fields=["domain"])
    assert site.domain == "updated_domain"


def test_update_tenant_no_allowed_origins(test_tenant):
    call_command(CMD, "--allowed-client-origins")

    test_tenant.refresh_from_db(fields=["allowed_client_origins"])
    assert test_tenant.allowed_client_origins == []


def test_update_tenant_allowed_hosts_wildcard(test_tenant):
    call_command(CMD, "--allowed-client-origins", "*")

    test_tenant.refresh_from_db(fields=["allowed_client_origins"])
    assert test_tenant.allowed_client_origins == ["*"]


def test_update_tenant_allowed_hosts_single_domain(test_tenant):
    call_command(CMD, "--allowed-client-origins", "https://otherdomain.com")

    test_tenant.refresh_from_db(fields=["allowed_client_origins"])
    assert test_tenant.allowed_client_origins == ["https://otherdomain.com"]


def test_update_tenant_allowed_hosts_multiple_domains(test_tenant):
    call_command(
        CMD, "--allowed-client-origins", "https://somedomain.com", "https://mirumee.com"
    )

    test_tenant.refresh_from_db(fields=["allowed_client_origins"])
    assert test_tenant.allowed_client_origins == [
        "https://somedomain.com",
        "https://mirumee.com",
    ]


def test_partial_update_limits(as_other_tenant, other_tenant):
    """Expect only two fields to be changed"""
    call_command(CMD, "--channels", 3, "--products", -1)
    fields = get_limits_fields()

    expected = {
        "max_channel_count": 3,  # from 2 to 3
        "max_staff_user_count": 3,
        "max_warehouse_count": 4,
        "max_sku_count": -1,  # from 5 to -1
    }

    # Retrieve all field from the model to ensure test is not outdated
    actual = Tenant.objects.filter(pk=other_tenant.pk).values(*fields).get()

    assert actual == expected
