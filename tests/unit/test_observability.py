import json

import pytest
from fastapi.testclient import TestClient

from api.main import app
from scripts.http_samples import percentile


@pytest.mark.parametrize(
    "values,expected", [([1], 1), (list(range(1, 21)), 19), (list(range(1, 101)), 95)]
)
def test_nearest_rank_p95(values, expected):
    assert percentile(values) == expected


def test_empty_samples_are_rejected():
    with pytest.raises(ValueError):
        percentile([])


def test_request_log_uses_route_template_and_no_private_values(capsys):
    with TestClient(app) as client:
        result = client.get(
            "/api/v1/orders/private-order?customer_id=private-customer",
            headers={
                "Idempotency-Key": "private-key-001",
                "Authorization": "Bearer private-token",
            },
        )
    assert result.status_code == 404
    output = capsys.readouterr().out
    row = json.loads(output.strip().splitlines()[-1])
    assert row["event"] == "http_request"
    assert row["route"] == "/api/v1/orders/{order_id}"
    assert row["status"] == 404
    assert all(
        value not in output
        for value in [
            "private-order",
            "private-customer",
            "private-key-001",
            "private-token",
        ]
    )
