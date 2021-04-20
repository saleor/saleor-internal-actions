from typing import TYPE_CHECKING

from .provider import meter

if TYPE_CHECKING is True:
    from ..models import Tenant


T_LABELS = dict


class Telemetry:
    __slots__ = ()

    _gql_request_counter = meter.create_counter(
        "request_gql",
        unit="1",
        value_type=int,
        description="Count POST /graphql/ requests",
    )

    @classmethod
    def get_tenant_labels(cls, tenant: "Tenant") -> T_LABELS:
        return {"project_id": tenant.project_id, "host": "", "model": "monthly"}

    @classmethod
    def inc_gql_request_count(cls, incr: int, labels: T_LABELS):
        """Increment the GraphQL request count metric for a specific tenant"""
        cls._gql_request_counter.add(incr, labels)
