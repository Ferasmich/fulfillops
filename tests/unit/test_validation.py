import pytest

from api.main import Problem, validate


def payload(quantity=1):
    return {
        "customer_id": "CUST-042",
        "items": [{"sku": "KIT-100", "quantity": quantity}],
    }


@pytest.mark.parametrize("quantity", [0, -1, 21, False, 1.5, "2", None])
def test_quantity_must_be_a_positive_bounded_integer(quantity):
    with pytest.raises(Problem) as error:
        validate(payload(quantity), "unit-test-key")
    assert error.value.code == "INVALID_QUANTITY"


@pytest.mark.parametrize("quantity", [1, 20])
def test_quantity_boundaries_are_accepted(quantity):
    assert (
        validate(payload(quantity), "unit-test-key")["items"][0]["quantity"] == quantity
    )


def test_equivalent_item_lines_normalize_identically():
    split = {
        "customer_id": "C",
        "items": [
            {"sku": "PART-200", "quantity": 1},
            {"sku": "KIT-100", "quantity": 1},
            {"sku": "PART-200", "quantity": 2},
        ],
    }
    joined = {
        "items": [
            {"quantity": 3, "sku": "PART-200"},
            {"quantity": 1, "sku": "KIT-100"},
        ],
        "customer_id": "C",
    }
    assert validate(split, "unit-test-key") == validate(joined, "unit-test-key")


def test_aggregate_can_exceed_per_line_limit():
    request = {"customer_id": "C", "items": [{"sku": "KIT-100", "quantity": 20}] * 10}
    assert validate(request, "unit-test-key")["items"] == [
        {"sku": "KIT-100", "quantity": 200}
    ]


@pytest.mark.parametrize("length", [0, 65])
def test_customer_id_length(length):
    request = payload()
    request["customer_id"] = "C" * length
    with pytest.raises(Problem) as error:
        validate(request, "unit-test-key")
    assert error.value.code == "INVALID_REQUEST"


@pytest.mark.parametrize("length", [8, 128])
def test_idempotency_key_boundaries(length):
    assert validate(payload(), "k" * length) == payload()


def test_unknown_extra_fields_are_rejected():
    request = payload()
    request["admin"] = True
    with pytest.raises(Problem) as error:
        validate(request, "unit-test-key")
    assert error.value.code == "INVALID_REQUEST"
