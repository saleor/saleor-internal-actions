from typing import Tuple

import pytest

from tenants.limits import collector
from tenants.limits.commands import collect_metrics as collect_metrics_command


@pytest.fixture
def metric_containers(
    test_tenant, other_tenant
) -> Tuple[
    collector.TenantMetricManager, collector.TenantMetrics, collector.TenantMetrics
]:
    manager = collect_metrics_command.make_default_manager()

    test_tenant_metrics = manager.create_tenant_metrics_container(
        schema_name=test_tenant.schema_name,
        host=test_tenant.domain_url,
        project_id=test_tenant.project_id,
        is_daily=False,
    )
    other_tenant_metrics = manager.create_tenant_metrics_container(
        schema_name=other_tenant.schema_name,
        host=other_tenant.domain_url,
        project_id=other_tenant.project_id,
        is_daily=True,
    )
    return manager, test_tenant_metrics, other_tenant_metrics
