import argparse
import json
from typing import List

from tenants.limits import models as m
from tenants.models import Tenant


class BillingOptionsParser:
    def __init__(self):
        self.parsed_options = {}

    @classmethod
    def make_example_help_text(cls) -> str:
        example = {
            "orders_hard_limited": True,
            "allowance_period": "monthly",
            **{f: -1 for f in m.LIMIT_FIELDS},
        }
        return json.dumps(example, indent=4)

    def set_defaults(self, **defaults) -> "BillingOptionsParser":
        self.parsed_options.update(defaults)
        return self

    def parse_from_dict(self, payload: dict):
        input_keys = set(payload.keys())
        expected_keys = m.FIELDS
        unknown_fields = input_keys.difference(expected_keys)

        if unknown_fields:
            raise ValueError("Unknown fields", unknown_fields)

        self.parsed_options.update(payload)

    def parse_from_str(self, input_string: str) -> "BillingOptionsParser":
        self.parse_from_dict(json.loads(input_string))
        return self

    def add_arguments(self, parser: argparse.ArgumentParser):
        group = parser.add_argument_group(
            "Billing Plan Limits",
            (
                "Set the environment plan usage limit constraints, example usage: \n"
                + self.make_example_help_text()
            ),
        )
        group.add_argument("--billing-opts", type=self.parse_from_str, default=self)

    def set_tenant_limits(self, tenant: Tenant) -> List[str]:
        """Set every provided limit to the given tenant"""
        updated = []
        for limit_field, limit_value in self.parsed_options.items():
            setattr(tenant, limit_field, limit_value)
            updated.append(limit_field)
        return updated
