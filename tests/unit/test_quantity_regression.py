import pytest

from api.main import Problem, validate


def test_boolean_quantity_is_rejected():
    request = {
        "customer_id": "CUST-042",
        "items": [{"sku": "KIT-100", "quantity": True}],
    }
    with pytest.raises(Problem) as result:
        validate(request, "regression-key-001")
    assert result.value.status == 422
    assert result.value.code == "INVALID_QUANTITY"
