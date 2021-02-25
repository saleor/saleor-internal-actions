from saleor.account.models import User
from tenants.limits.middleware import TenantPlanLimitMiddleware


def test_limit_staff_count_only_counts_staff(as_other_tenant):
    """Ensure it is only counting for only staff users."""
    tenant = as_other_tenant
    tenant.max_staff_user_count = 1

    User.objects.bulk_create(
        [
            User(email="staff@example.com", is_staff=True),
            User(email="superuser@example.com", is_staff=True, is_superuser=True),
        ]
    )

    # Check actual queryset
    result = TenantPlanLimitMiddleware.is_mutation_allowed(tenant, "staffCreate")
    assert result.data["current"] == 2

    # Should not change
    User.objects.create(email="customer@example.com")
    result = TenantPlanLimitMiddleware.is_mutation_allowed(tenant, "staffCreate")
    assert result.data["current"] == 2
