from typing import Union, Type, Optional

from django.db import connection

from saleor.order.models import Order
from .. import middleware as limits_middleware

T_LIMIT_RESOLVER = Union[Type["AllowedUsageResolver"], Type["CurrentUsageResolver"]]


class CurrentUsageResolver:
    @staticmethod
    def channels():
        return limits_middleware.channel_limit.qs.count()

    @staticmethod
    def orders():
        return Order.objects.count()

    @staticmethod
    def product_variants():
        return limits_middleware.sku_limit.qs.count()

    @staticmethod
    def staff_users():
        return limits_middleware.staff_users_limit.qs.count()

    @staticmethod
    def warehouses():
        return limits_middleware.warehouse_limit.qs.count()


class AllowedUsageResolver:
    @classmethod
    def format_value(cls, value: int):
        if value == -1:
            return None
        return value

    @classmethod
    def channels(cls):
        return cls.format_value(connection.tenant.max_channel_count)

    @classmethod
    def orders(cls):
        # Not currently implemented in multi-tenant
        return None

    @classmethod
    def product_variants(cls):
        return cls.format_value(connection.tenant.max_sku_count)

    @classmethod
    def staff_users(cls):
        return cls.format_value(connection.tenant.max_staff_user_count)

    @classmethod
    def warehouses(cls):
        return cls.format_value(connection.tenant.max_warehouse_count)


class LimitType:
    def __init__(self, resolver: T_LIMIT_RESOLVER, *args, **kwargs):
        self._limit_resolver = resolver
        super().__init__(*args, **kwargs)


def default_resolver(attname: str, _default_value: None, root: LimitType, _info, **_) -> Optional[int]:
    resolver_cls: T_LIMIT_RESOLVER = root._limit_resolver
    resolver_func = getattr(resolver_cls, attname)
    result: Optional[int] = resolver_func()
    return result
