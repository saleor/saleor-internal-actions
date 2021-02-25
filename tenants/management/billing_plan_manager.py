import argparse
from functools import partial
from typing import Any

from tenants.models import Tenant
from tenants.limits import models as m

T_LIMITS = dict[str, int]


class BillingPlanManagement:
    @classmethod
    def extract_limits_from_opts(cls, options: dict[str, Any]) -> T_LIMITS:
        return {
            k: v for k, v in options.items() if k.startswith("max_") and v is not None
        }

    @classmethod
    def add_arguments(
        cls, parser: argparse.ArgumentParser, default: int = None, required: bool = True
    ):
        group = parser.add_argument_group(
            "Billing Plan Limits", "Set the environment plan usage limit constraints"
        )
        add_argument = partial(
            group.add_argument, type=int, default=default, required=required,
        )

        add_argument("--products", dest=m.MAX_SKU_COUNT)
        add_argument("--channels", dest=m.MAX_CHANNEL_COUNT)
        add_argument("--warehouses", dest=m.MAX_WAREHOUSE_COUNT)
        add_argument("--staff", dest=m.MAX_STAFF_USER_COUNT)

    @classmethod
    def set_tenant_limits(cls, tenant: Tenant, limits: T_LIMITS):
        """Set every provided limit to the given tenant"""
        for limit_field, limit_value in limits.items():
            setattr(tenant, limit_field, limit_value)
