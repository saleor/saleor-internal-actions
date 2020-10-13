import pytest

from django.core.management.base import CommandError
from django.contrib.sites.models import Site
from django.core.management import call_command
from tenant_schemas.utils import tenant_context

from tenants.models import Tenant

CMD = "updatedomain"


def test_update_tenant_domain(test_tenant):
    call_command(CMD, test_tenant.domain_url, "new_domain")

    tenant = Tenant.objects.get(id=test_tenant.id)
    assert tenant.domain_url == "new_domain"
    with tenant_context(tenant):
        site = Site.objects.get()
        assert site.domain == "new_domain"


def test_update_non_existing_tenant_domain():
    with pytest.raises(CommandError):
        call_command(CMD, "non_existing", "new_domain")


def test_update_tenant_which_changed_site_domain(test_tenant):
    with tenant_context(test_tenant):
        site = Site.objects.get()
        site.domain = "updated_domain"
        site.save()

    call_command(CMD, test_tenant.domain_url, "new_domain")

    tenant = Tenant.objects.get(id=test_tenant.id)
    assert tenant.domain_url == "new_domain"
    assert site.domain == "updated_domain"
