import argparse
from functools import partial
from typing import Any, Union

from tenants.limits import models as m
from tenants.models import Tenant

T_LIMITS = dict[str, Union[int, str]]


class BillingPlanManagement:
    @classmethod
    def extract_limits_from_opts(cls, options: dict[str, Any]) -> T_LIMITS:
        """
        Extracts all billing information fields from the parsed namespace
        
        Expects all fields to be supplied:
        - If the parameters are not required, we expect non-null defaults for missing values
        - If the parameters are all required, we expect only user inputs as values
        
        If the two conditions are not true, a `KeyError` exception is expected.
        """
        found = {}
        for field_name in m.FIELDS:
            value = options[field_name]
            if value is not None:
                found[field_name] = value
        return found

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

        if required is True:
            group.add_argument(
                "--allowance-period", dest=m.ALLOWANCE_PERIOD, required=True
            )
        else:
            group.add_argument(
                "--allowance-period",
                dest=m.ALLOWANCE_PERIOD,
                required=False,
                default="monthly",
            )

    @classmethod
    def set_tenant_limits(cls, tenant: Tenant, limits: T_LIMITS):
        """Set every provided limit to the given tenant"""
        for limit_field, limit_value in limits.items():
            setattr(tenant, limit_field, limit_value)
