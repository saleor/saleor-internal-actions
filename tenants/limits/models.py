from django.db import models
from django.db.models import QuerySet

from tenants.postgresql_backend.base import DatabaseWrapper as TenantConnection

connection: TenantConnection

ORDERS_HARD_LIMITED = "orders_hard_limited"
MAX_STAFF_USER_COUNT = "max_staff_user_count"
MAX_WAREHOUSE_COUNT = "max_warehouse_count"
MAX_CHANNEL_COUNT = "max_channel_count"
MAX_SKU_COUNT = "max_sku_count"
MAX_ORDER_COUNT = "max_order_count"
ALLOWANCE_PERIOD = "allowance_period"

LIMIT_FIELDS = {
    MAX_STAFF_USER_COUNT,
    MAX_WAREHOUSE_COUNT,
    MAX_CHANNEL_COUNT,
    MAX_SKU_COUNT,
    MAX_ORDER_COUNT,
}

BILLING_INFO_FIELDS = {
    ORDERS_HARD_LIMITED,
    ALLOWANCE_PERIOD,
}

FIELDS = {
    *LIMIT_FIELDS,
    *BILLING_INFO_FIELDS,
}


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
        * Orders: includes draft orders
    """

    orders_hard_limited = models.BooleanField()

    max_staff_user_count = models.IntegerField()
    max_warehouse_count = models.IntegerField()
    max_channel_count = models.IntegerField()
    max_sku_count = models.IntegerField()
    max_order_count = models.IntegerField()

    allowance_period = models.CharField(max_length=20)

    objects: QuerySet

    class Meta:
        abstract = True
