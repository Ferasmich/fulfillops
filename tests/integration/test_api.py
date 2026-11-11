import httpx
import pytest
from fastapi.testclient import TestClient

from api.main import app
from common.database import connect
from db.manage import migrate, seed
from db.manage import test_target as check_test_target
from tests.helpers import server

client = TestClient(app)


def body(items=None):
    return {
        "customer_id": "CUST-042",
        "items": items or [{"sku": "KIT-100", "quantity": 1}],
    }


def post(payload=None, key="example-key-001"):
    return client.post(
        "/api/v1/orders", json=payload or body(), headers={"Idempotency-Key": key}
    )


def stock(sku="KIT-100"):
    return client.get("/api/v1/inventory/" + sku).json()["available"]


def test_catalog_health_and_metrics():
    assert client.get("/health/live").json() == {"status": "ok"}
    assert client.get("/health/ready").json() == {"status": "ready"}
    assert {
        p["sku"]: p["unit_price_cents"]
        for p in client.get("/api/v1/catalog").json()["products"]
    } == {"KIT-100": 1299, "PART-200": 599, "PACK-300": 249}
    result = client.get("/metrics")
    assert result.status_code == 200
    for name in ["orders_created", "orders_failed", "worker_retries", "http_requests"]:
        assert "fulfillops_" + name + "_total" in result.text
    assert "fulfillops_http_request_duration_seconds_bucket" in result.text


def test_receipt_replay_conflict_and_durable_job():
    first = post()
    assert first.status_code == 202
    assert first.json()["status"] == "queued"
    assert post().json() == first.json()
    assert stock() == 6
    order = client.get("/api/v1/orders/" + first.json()["order_id"]).json()
    assert order["total_cents"] == 1299
    assert order["status"] == "queued"
    conflict = post({"customer_id": "another", "items": body()["items"]})
    assert conflict.status_code == 409
    assert conflict.json()["error"]["code"] == "IDEMPOTENCY_CONFLICT"
    with connect() as conn:
        assert conn.execute("SELECT count(*) AS n FROM orders").fetchone()["n"] == 1
        assert conn.execute("SELECT count(*) AS n FROM jobs").fetchone()["n"] == 1
    print("Replay: one order, one job, KIT-100 stock 7 -> 6; changed payload rejected")


@pytest.mark.parametrize("quantity", [0, -1, 21, True, 1.5, "1", None])
def test_invalid_quantity(quantity):
    result = post(body([{"sku": "KIT-100", "quantity": quantity}]))
    assert result.status_code == 422
    assert result.json()["error"]["code"] == "INVALID_QUANTITY"
    assert stock() == 7


@pytest.mark.parametrize(
    "payload,code",
    [
        ({}, "INVALID_REQUEST"),
        ({"customer_id": "", "items": []}, "INVALID_REQUEST"),
        (
            {"customer_id": "C", "items": [{"sku": "NOPE", "quantity": 1}]},
            "INVALID_SKU",
        ),
    ],
)
def test_invalid_request(payload, code):
    result = client.post(
        "/api/v1/orders", json=payload, headers={"Idempotency-Key": "example-key-001"}
    )
    assert result.json()["error"]["code"] == code
    assert result.status_code == (422 if code == "INVALID_SKU" else 400)


def test_missing_key_invalid_json_and_unknown_resources():
    assert (
        client.post("/api/v1/orders", json=body()).json()["error"]["code"]
        == "IDEMPOTENCY_REQUIRED"
    )
    assert (
        client.post(
            "/api/v1/orders",
            content=b"{",
            headers={"Idempotency-Key": "example-key-001"},
        ).json()["error"]["code"]
        == "INVALID_JSON"
    )
    for path, code in [
        ("/api/v1/orders/not-a-uuid", "ORDER_NOT_FOUND"),
        ("/api/v1/inventory/NOPE", "SKU_NOT_FOUND"),
    ]:
        result = client.get(path)
        assert result.status_code == 404
        assert result.json()["error"]["code"] == code


def test_body_limit_streamed_without_length():
    def chunks():
        yield b" " * 8192
        yield b" " * 8193

    result = client.post(
        "/api/v1/orders",
        content=chunks(),
        headers={"Idempotency-Key": "example-key-001"},
    )
    assert result.status_code == 413
    assert result.json()["error"]["code"] == "REQUEST_TOO_LARGE"


def test_aggregation_normalization_and_total():
    payload = body(
        [{"sku": "PACK-300", "quantity": 2}, {"sku": "PACK-300", "quantity": 2}]
    )
    result = post(payload)
    assert result.status_code == 202
    assert stock("PACK-300") == 1
    assert (
        client.get("/api/v1/orders/" + result.json()["order_id"]).json()["total_cents"]
        == 996
    )
    assert post(body([{"quantity": 4, "sku": "PACK-300"}])).json() == result.json()


def test_insufficient_stock_rolls_back_whole_order():
    result = post(
        body([{"sku": "KIT-100", "quantity": 1}, {"sku": "PACK-300", "quantity": 6}])
    )
    assert result.status_code == 409
    assert result.json()["error"]["code"] == "OUT_OF_STOCK"
    assert stock() == 7
    assert stock("PACK-300") == 5
    with connect() as conn:
        for table in ["orders", "order_requests", "jobs"]:
            from psycopg import sql

            assert (
                conn.execute(
                    sql.SQL("SELECT count(*) AS n FROM {}").format(
                        sql.Identifier(table)
                    )
                ).fetchone()["n"]
                == 0
            )
    assert post().status_code == 202  # Rejected requests do not consume the key.
    print(
        "Insufficient multi-item order: no partial allocation or orphan order/key/job"
    )


def test_migrations_and_seed_do_not_reset_stock():
    post()
    migrate()
    seed()
    assert stock() == 6
    with connect() as conn:
        assert (
            conn.execute("SELECT count(*) AS n FROM schema_migrations").fetchone()["n"]
            == 3
        )


def test_seed_rejects_non_test_environment(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    with pytest.raises(RuntimeError):
        check_test_target()


def test_readiness_storage_failure_does_not_break_liveness(monkeypatch):
    monkeypatch.setenv("DB_PORT", "1")
    assert client.get("/health/ready").status_code == 503
    assert client.get("/health/live").status_code == 200


def test_real_api_restart_preserves_replay():
    with server() as (url, pid):
        first = httpx.post(
            url + "/api/v1/orders",
            json=body(),
            headers={"Idempotency-Key": "restart-key-001"},
        )
        assert first.status_code == 202
    with server() as (url, next_pid):
        replay = httpx.post(
            url + "/api/v1/orders",
            json=body(),
            headers={"Idempotency-Key": "restart-key-001"},
        )
        assert replay.status_code == 202
        assert replay.json() == first.json()
        assert httpx.get(url + "/api/v1/inventory/KIT-100").json()["available"] == 6
    print(
        f"API restart {pid} -> {next_pid}: stable order {first.json()['order_id']}; stock stays 6"
    )


def test_multi_product_total_and_completed_receipt():
    result = post(
        body([{"sku": "KIT-100", "quantity": 1}, {"sku": "PART-200", "quantity": 2}])
    )
    assert result.status_code == 202
    order_id = result.json()["order_id"]
    assert client.get("/api/v1/orders/" + order_id).json()["total_cents"] == 2497
    # Fixture state only: this does not demonstrate a working worker.
    with connect() as conn:
        conn.execute("UPDATE orders SET status='completed' WHERE id=%s", (order_id,))
    assert (
        post(
            body(
                [{"sku": "PART-200", "quantity": 2}, {"sku": "KIT-100", "quantity": 1}]
            )
        ).json()
        == result.json()
    )
    assert stock() == 6
    assert stock("PART-200") == 10


@pytest.mark.parametrize("key", ["short", "x" * 129, "tab\tkey-000"])
def test_invalid_idempotency_key(key):
    result = post(key=key)
    assert result.status_code == 400
    assert result.json()["error"]["code"] == "INVALID_REQUEST"


def test_database_rejects_negative_stock():
    import psycopg

    with pytest.raises(psycopg.errors.CheckViolation), connect() as conn:
        conn.execute("UPDATE products SET available=-1 WHERE sku='KIT-100'")
    assert stock() == 7


def test_modified_applied_migration_is_rejected():
    with connect() as conn:
        original = conn.execute(
            "SELECT checksum FROM schema_migrations WHERE version='001_products.sql'"
        ).fetchone()["checksum"]
        conn.execute(
            "UPDATE schema_migrations SET checksum='changed' WHERE version='001_products.sql'"
        )
    try:
        with pytest.raises(RuntimeError, match="Applied migration changed"):
            migrate()
    finally:
        with connect() as conn:
            conn.execute(
                "UPDATE schema_migrations SET checksum=%s WHERE version='001_products.sql'",
                (original,),
            )
