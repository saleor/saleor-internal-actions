import pytest

from tenants.management.billing_plan_manager import BillingOptionsParser


def test_rejects_unknown_fields():
    payload = {
        "pk": "123",
        "id": "123",
        "_internal": "foo",
        "allowance_period": "valid",
    }
    parser = BillingOptionsParser()

    with pytest.raises(ValueError) as exc:
        parser.parse_from_dict(payload)

    assert exc.value.args == ("Unknown fields", {"pk", "id", "_internal"})
