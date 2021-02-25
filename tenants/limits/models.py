from django.db import models
from django.db.models import QuerySet

from tenants.postgresql_backend.base import DatabaseWrapper as TenantConnection

connection: TenantConnection

MAX_STAFF_USER_COUNT = "max_staff_user_count"
MAX_WAREHOUSE_COUNT = "max_warehouse_count"
MAX_CHANNEL_COUNT = "max_channel_count"
MAX_SKU_COUNT = "max_sku_count"


class TenantLimitsMixin(models.Model):
    """
    Mixin containing tenant's plan limits

    Each field prefixed by "max_" defines the maximum count allowed of given
    database entries for a specific tenant.

    *  0 => no entry allowed
    * -1 => unlimited

    Note: NULL is not an allowed value to prevent accidental bug(s) where the software
          could potentially and unnoticeably not set a value and thus flagging a tenant
          as "unlimited plan".

    Fields:
        * Staff Users: users having for flag "is_staff" and/or "is_superuser"
        * Warehouses: stock locations
        * Channels: currencies available for the shop
        * SKUs: the number of product variants (a product always have at least 1 variant)
    """

    max_staff_user_count = models.IntegerField()
    max_warehouse_count = models.IntegerField()
    max_channel_count = models.IntegerField()
    max_sku_count = models.IntegerField()

    objects: QuerySet

    class Meta:
        abstract = True
