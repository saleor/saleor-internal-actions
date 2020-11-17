from django.contrib.sites.models import Site
from django.core.management import call_command
from tenant_schemas.utils import tenant_context

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
