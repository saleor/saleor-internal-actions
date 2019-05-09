from django.db import models
from django.core.management.utils import get_random_secret_key
from tenant_schemas.models import TenantMixin


class Tenant(TenantMixin):
    created_on = models.DateField(auto_now_add=True)
    jwt_secret_key = models.CharField(max_length=50, default=get_random_secret_key)

    auto_create_schema = True
    auto_drop_schema = True
