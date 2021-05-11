import datetime
import functools
from collections import namedtuple
from typing import List, Optional

import opentracing as ot
from django import db


ALL_TENANTS_STATS_QUERY = """
SELECT 
    S.schemaname                  AS schema_name,
    T.domain_url                  AS host,
    T.project_id                  AS project_id,
    T.allowance_period = 'daily'  AS is_daily,
    S.relname                     AS table_name,
    S.n_live_tup                  AS live_count

FROM pg_catalog.pg_stat_all_tables AS S
JOIN public.tenants_tenant AS T ON S.schemaname = T.schema_name

WHERE relname IN (
    'product_productvariant', 
    'warehouse_warehouse', 
    'channel_channel'
)
ORDER BY T.domain_url;
"""

CONDITIONAL_SINGLE_TENANT_QUERY = """
SELECT 
    (SELECT COUNT(*) FROM account_user WHERE account_user.is_staff) as staff_count,
    (SELECT COUNT(*) FROM order_order WHERE order_order.created >= %s::timestamp) as order_count
;
"""

MetricRecord = namedtuple(
    "MetricRecord",
    ("schema_name", "host", "project_id", "is_daily", "table_name", "live_count"),
)


def trace(func):
    name = getattr(func, "__name__", None) or getattr(func, "__qualname__")

    @functools.wraps(func)
    def _trace(*args, **kwargs):
        with ot.global_tracer().start_active_span(name) as _span:
            return func(*args, **kwargs)

    return _trace


class TenantMetrics:
    __slots__ = (
        "schema_name",
        "project_id",
        "host",
        "is_daily",
        "orders",
        "variants",
        "warehouses",
        "channels",
        "staff_users",
    )

    def __init__(self, *, schema_name: str, project_id: int, host: str, is_daily: bool):
        self.is_daily: bool = is_daily
        self.schema_name: str = schema_name
        self.project_id: int = project_id
        self.host: str = host

        self.orders: int = 0
        self.variants: int = 0
        self.warehouses: int = 0
        self.channels: int = 0
        self.staff_users: int = 0

    def as_dict(self) -> dict:
        return {
            "host": self.host,
            "project_id": self.project_id,
            "orders": self.orders,
            "variants": self.variants,
            "warehouses": self.warehouses,
            "channels": self.channels,
            "staff_users": self.staff_users,
        }

    def increment(self, field: str, by: int):
        initial = getattr(self, field)
        setattr(self, field, initial + by)

    def __str__(self):
        return str(self.as_dict())


REL_MAP = {
    "product_productvariant": "variants",
    "warehouse_warehouse": "warehouses",
    "channel_channel": "channels",
}


class TenantMetricManager:
    __slots__ = ("tenants", "start_day_datetime", "start_month_datetime")

    def __init__(
        self, start_day_datetime: datetime.date, start_month_datetime: datetime.datetime
    ):
        self.tenants: List[TenantMetrics] = []
        self.start_day_datetime = start_day_datetime
        self.start_month_datetime = start_month_datetime

    @staticmethod
    def get_connection():
        return db.connection

    @trace
    def create_tenant_metrics_container(
        self, schema_name: str, host: str, project_id: int, is_daily: bool,
    ) -> TenantMetrics:
        """Creates a tenant metrics container that holds all the gathered metrics."""
        metrics = TenantMetrics(
            schema_name=schema_name, project_id=project_id, host=host, is_daily=is_daily
        )
        self.tenants.append(metrics)
        return metrics

    @trace
    def _collect_complex_metrics(self):
        """
        Send a SQL query for every tenant returning the count of filtered queries.

        Currently only processes the staff users count.

        This is unoptimized. It sends two query per tenant:
            1. Sets the PgSQL namespace
            2. Gets the count

        A possibility could be having a view containing all the staff users
        then in pg_class retrieve the number of tuples. But it would mean
        having to vacuum often. https://www.postgresql.org/docs/11/catalog-pg-class.html

        Docs are mentioning the following:
        > It is updated by VACUUM, ANALYZE, and a few DDL commands such as CREATE INDEX.
                                            ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

        Potentially one could index the ``is_staff`` column and (MAYBE) would result
        to pg_class to get updated more frequently.
        """
        today_start, this_month_start = (
            self.start_day_datetime,
            self.start_month_datetime,
        )
        connection = self.get_connection()

        for tenant in self.tenants:
            connection.set_schema(tenant.schema_name)

            with connection.cursor() as cur:
                if tenant.is_daily is True:
                    cur.execute(CONDITIONAL_SINGLE_TENANT_QUERY, (today_start,))
                else:
                    cur.execute(CONDITIONAL_SINGLE_TENANT_QUERY, (this_month_start,))
                staff, orders = cur.fetchone()

            tenant.orders += orders
            tenant.staff_users += staff

        connection.set_schema_to_public()

    @trace
    def _collect_basic_metrics(self):
        """
        Retrieves the number of rows for given tables in a single SQL query.

        The tables to which the count of rows must be retrieved is defined by the
        WHERE condition in ``ALL_TENANTS_STATS_QUERY``.

        Each record comes from the database's global statistic table and is then
        associated to the database's global tenant table.

        More information at https://www.postgresql.org/docs/11/monitoring-stats.html
        """
        connection = self.get_connection()

        with connection.cursor() as cursor:
            cursor.execute(ALL_TENANTS_STATS_QUERY)
            host: str = ""
            current_tenant: Optional[TenantMetrics] = None

            # Store all the rows to be grouped into a single object per tenant
            for row in cursor.fetchall():
                # Parse the row
                record = MetricRecord(*row)

                # get the data until the next tenant appears
                if record.host != host:
                    host = record.host
                    current_tenant = self.create_tenant_metrics_container(
                        record.schema_name,
                        record.host,
                        record.project_id,
                        record.is_daily,
                    )

                # Increment associated SQL table to simple API field key
                # e.g. channel_channel => channels
                field = REL_MAP[record.table_name]
                current_tenant.increment(field, record.live_count)

    @trace
    def collect_metrics(self):
        # * Collect basic metrics: the row count of specific tables
        # * Collect "complex" metrics: row count with WHERE conditions
        self._collect_basic_metrics()
        self._collect_complex_metrics()

    @trace
    def as_list(self) -> list:
        return [tenant.as_dict() for tenant in self.tenants]

    def __str__(self):
        return "\n".join(str(t) for t in self.tenants)
