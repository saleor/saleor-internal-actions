from datetime import datetime
from typing import Any, Callable, Dict, Optional, Union

from django.conf import settings
from django.db import connection
from django.db.models import Manager, QuerySet
from graphql import ResolveInfo
from graphql.language.ast import Field

import saleor.account.models as user_models
import saleor.channel.models as channel_models
import saleor.product.models as product_models
import saleor.order.models as order_models
import saleor.warehouse.models as warehouse_models
from tenants.models import Tenant
from tenants.telemetry.controller import Telemetry

from . import errors
from . import models as m


class LimitInfo:
    __slots__ = (
        "resource_plural",
        "tenant_field",
        "qs",
        "hard_limited_field_name",
    )

    def __init__(
        self,
        resource_plural: str,
        tenant_field: str,
        qs: Union[QuerySet, Manager],
        hard_limited_field_name: str = None,
    ):
        """
        :param resource_plural: name of the resource that is limited
        :param tenant_field: field of tenant to retrieve limit from
        :param qs: lookup for determining usage, will be invoked with ``count()``
        :param hard_limited_field:
            - When a hard-limited flag exists and resolves to False, skip the check.
            - When hard-limited flag does not exist, it is always hard-limited,
              thus check.
        """
        self.resource_plural = resource_plural
        self.tenant_field = tenant_field
        self.qs = qs
        self.hard_limited_field_name = hard_limited_field_name

    def is_hard_limited(self, tenant: Tenant) -> bool:
        if self.hard_limited_field_name is None:
            return True
        return getattr(tenant, self.hard_limited_field_name)

    def get_qs(self, tenant: Tenant):
        return self.qs

    def check_limit(self, tenant: Tenant) -> Optional[errors.LimitReachedException]:
        # Check if tenant should be hard limited for that mutation
        # If the tenant is not hard-limited, then skip checking usage
        if self.is_hard_limited(tenant) is False:
            return None

        maximum: int = getattr(tenant, self.tenant_field)

        # Skip getting the current count if the value is -1, means they are unlimited
        if maximum == -1:
            return None

        # Retrieve the count of the limited entries
        qs = self.get_qs(tenant)
        current: int = qs.count()

        if current >= maximum:
            return errors.LimitReachedException(
                resource_plural=self.resource_plural,
                maximum_count=maximum,
                current=current,
            )
        return None


class OrderLimit(LimitInfo):
    def get_qs(self, tenant: Tenant):
        now_dt = datetime.now()

        # Retrieve the start day from which to count
        if tenant.allowance_period == "daily":
            day = now_dt.day
        elif tenant.allowance_period == "monthly":
            day = 1
        else:
            raise RuntimeError("Unknown allowance period", tenant.allowance_period)

        # Exclude orders outside of the current allowance range
        after_dt = datetime(now_dt.year, now_dt.month, day)
        qs = self.qs.filter(created__gte=after_dt)
        return qs


staff_users_limit = LimitInfo(
    "Staff Users",
    m.MAX_STAFF_USER_COUNT,
    user_models.User.objects.filter(is_staff=True),
)
sku_limit = LimitInfo("SKUs", m.MAX_SKU_COUNT, product_models.ProductVariant.objects)
warehouse_limit = LimitInfo(
    "Warehouses", m.MAX_WAREHOUSE_COUNT, warehouse_models.Warehouse.objects
)
channel_limit = LimitInfo(
    "Channels", m.MAX_CHANNEL_COUNT, channel_models.Channel.objects
)

order_limit = OrderLimit(
    "Orders",
    m.MAX_ORDER_COUNT,
    order_models.Order.objects,
    hard_limited_field_name="orders_hard_limited",
)


class TenantPlanLimitMiddleware:
    LIMITED_MUTATIONS: Dict[str, LimitInfo] = {
        # Staff
        "staffCreate": staff_users_limit,
        # SKU
        # Blocks product creations as well due to not being atomic operations
        # meaning dashboard will create a product and then try to create variants
        "productVariantCreate": sku_limit,
        "productCreate": sku_limit,
        # Warehouse
        "warehouseCreate": warehouse_limit,
        # Channel
        "channelCreate": channel_limit,
        # Blocks checkouts and draft orders
        "checkoutComplete": order_limit,
        "draftOrderCreate": order_limit,
    }

    @classmethod
    def is_mutation_allowed(
        cls, tenant: Tenant, field_name: str
    ) -> Optional[errors.LimitReachedException]:
        limit_info: Optional[LimitInfo] = cls.LIMITED_MUTATIONS.get(field_name)

        # Skip if there is no limits associated to that mutation name
        if limit_info is None:
            return None

        # Check if the user can proceed on that tenant, i.e. has enough slots
        error_result = limit_info.check_limit(tenant)
        return error_result

    @classmethod
    def check_limits(cls, info: ResolveInfo) -> Optional[errors.LimitReachedException]:
        """
        Checks whether or not the user can proceed with the action.

        It will go through every root selections of a query. For example:

        ```graphql
        mutation {
          staffUpdate(...) {  # <-- mutation call #1
            foo
          }
          staffCreate(...) {  # <-- mutation call #2
            bar
          }
        }
        ```

        The below code will check `staffUpdate` and `staffCreate` but not go into them.
        """
        tenant = connection.tenant

        # Iterate the root fields
        selection: Field
        for selection in info.operation.selection_set.selections:
            field_name: str = selection.name.value
            error_result = cls.is_mutation_allowed(tenant, field_name)

            # If there is an error (out of limits), abort their request and return it
            if error_result is not None:
                return error_result
        return None

    @classmethod
    def handle_root_resolve(
        cls, info: ResolveInfo
    ) -> Optional[errors.LimitReachedException]:
        # Retrieve annotations for the tenant and cache it
        labels = Telemetry.get_tenant_labels(connection.tenant)

        # Increment GraphQL request count otherwise other requests such as plugins
        # GraphQL requests can have trailing characters after the slash
        if settings.OPTL_ENABLED is True:
            Telemetry.inc_gql_request_count(1, labels)

        # If the call is write operation, check limits
        if info.operation.operation == "mutation":
            result = cls.check_limits(info)
            return result
        return None

    @classmethod
    def resolve(cls, next_: Callable, root: object, info: ResolveInfo, **kwargs: Any):
        # Only run the middleware for the root resolver
        if root is None:
            error = cls.handle_root_resolve(info)
            if error is not None:
                return error
        return next_(root, info, **kwargs)
