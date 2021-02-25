from django.core.management.utils import get_random_secret_key
from django.db import models
from tenant_schemas.models import TenantMixin

from tenants.limits.models import TenantLimitsMixin


def default_allowed_client_origins():
    return ["*"]


class Tenant(TenantLimitsMixin, TenantMixin, models.Model):
    created_on = models.DateField(auto_now_add=True)
    jwt_secret_key = models.CharField(max_length=50, default=get_random_secret_key)
    allowed_client_origins = models.JSONField(default=default_allowed_client_origins)

    # Contains the Environment's Project ID from Cloud-API
    project_id = models.IntegerField(null=False)

    auto_create_schema = True
    auto_drop_schema = True
