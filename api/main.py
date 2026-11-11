import json
import time
from datetime import UTC, datetime
from uuid import UUID, uuid4

import psycopg
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response
from prometheus_client import CollectorRegistry, Counter, Histogram, generate_latest
from psycopg.types.json import Jsonb
from starlette.concurrency import run_in_threadpool
from starlette.exceptions import HTTPException

from common.database import connect
from db.manage import migration_files

app = FastAPI(title="FulfillOps", docs_url=None, redoc_url=None, openapi_url=None)
registry = CollectorRegistry()
requests = Counter(
    "fulfillops_http_requests_total",
    "HTTP requests",
    ["method", "route", "status"],
    registry=registry,
)
latency = Histogram(
    "fulfillops_http_request_duration_seconds",
    "HTTP latency",
    ["method", "route"],
    registry=registry,
)
SKUS = {"KIT-100", "PART-200", "PACK-300"}


class Problem(Exception):
    def __init__(self, status, code, message):
        self.status, self.code, self.message = status, code, message


def error(status, code, message):
    return JSONResponse(
        {"error": {"code": code, "message": message}}, status_code=status
    )


@app.exception_handler(Problem)
async def problem_handler(request, exc):
    return error(exc.status, exc.code, exc.message)


@app.exception_handler(psycopg.Error)
async def database_handler(request, exc):
    return error(503, "SERVICE_UNAVAILABLE", "Storage temporarily unavailable")


@app.exception_handler(HTTPException)
async def http_handler(request, exc):
    return error(
        exc.status_code,
        "NOT_FOUND" if exc.status_code == 404 else "INVALID_REQUEST",
        "Request cannot be handled",
    )


@app.middleware("http")
async def measure(request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    route = request.scope.get("route")
    path = route.path if route else "unmatched"
    method = (
        request.method
        if request.method
        in {"GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"}
        else "OTHER"
    )
    requests.labels(method, path, str(response.status_code)).inc()
    duration = time.perf_counter() - start
    latency.labels(method, path).observe(duration)
    print(
        json.dumps(
            {
                "time": datetime.now(UTC).isoformat(),
                "event": "http_request",
                "method": method,
                "route": path,
                "status": response.status_code,
                "duration_seconds": round(duration, 6),
            }
        ),
        flush=True,
    )
    return response


@app.get("/health/live")
def live():
    return {"status": "ok"}


@app.get("/health/ready")
def ready():
    try:
        with connect() as conn:
            versions = {
                r["version"]
                for r in conn.execute("SELECT version FROM schema_migrations")
            }
            if not {f.name for f in migration_files()} <= versions:
                return JSONResponse({"status": "not_ready"}, status_code=503)
    except psycopg.Error:
        return JSONResponse({"status": "not_ready"}, status_code=503)
    return {"status": "ready"}


@app.get("/api/v1/catalog")
def catalog():
    with connect() as conn:
        return {
            "products": conn.execute(
                "SELECT sku, unit_price_cents FROM products ORDER BY sku"
            ).fetchall()
        }


@app.get("/api/v1/inventory/{sku}")
def inventory(sku: str):
    with connect() as conn:
        row = conn.execute(
            "SELECT sku, available FROM products WHERE sku=%s", (sku,)
        ).fetchone()
    if not row:
        raise Problem(404, "SKU_NOT_FOUND", "Product not found")
    return row


def validate(body, key):
    if key is None:
        raise Problem(400, "IDEMPOTENCY_REQUIRED", "Idempotency-Key is required")
    if not 8 <= len(key) <= 128 or any(not 32 <= ord(c) <= 126 for c in key):
        raise Problem(400, "INVALID_REQUEST", "Invalid Idempotency-Key")
    if not isinstance(body, dict) or set(body) != {"customer_id", "items"}:
        raise Problem(400, "INVALID_REQUEST", "Expected customer_id and items")
    customer, items = body["customer_id"], body["items"]
    if not isinstance(customer, str) or not 1 <= len(customer) <= 64:
        raise Problem(400, "INVALID_REQUEST", "Invalid customer_id")
    if not isinstance(items, list) or not 1 <= len(items) <= 10:
        raise Problem(400, "INVALID_REQUEST", "Expected between 1 and 10 items")
    combined = {}
    for item in items:
        if not isinstance(item, dict) or set(item) != {"sku", "quantity"}:
            raise Problem(400, "INVALID_REQUEST", "Expected sku and quantity")
        sku, quantity = item["sku"], item["quantity"]
        if type(quantity) is not int or not 1 <= quantity <= 20:
            raise Problem(
                422, "INVALID_QUANTITY", "Quantity must be an integer from 1 to 20"
            )
        if not isinstance(sku, str) or sku not in SKUS:
            raise Problem(422, "INVALID_SKU", "Unknown product")
        combined[sku] = combined.get(sku, 0) + quantity
    return {
        "customer_id": customer,
        "items": [{"sku": s, "quantity": q} for s, q in sorted(combined.items())],
    }


def accept(payload, key):
    for attempt in range(3):
        try:
            with connect() as conn:
                order_id = uuid4()
                inserted = conn.execute(
                    """INSERT INTO order_requests(key, canonical_payload, order_id)
                    VALUES (%s, %s, %s) ON CONFLICT (key) DO NOTHING RETURNING key""",
                    (key, Jsonb(payload), order_id),
                ).fetchone()
                if not inserted:
                    row = conn.execute(
                        "SELECT canonical_payload, order_id FROM order_requests WHERE key=%s",
                        (key,),
                    ).fetchone()
                    if row["canonical_payload"] != payload:
                        raise Problem(
                            409,
                            "IDEMPOTENCY_CONFLICT",
                            "Key already belongs to a different request",
                        )
                    order_id = row["order_id"]
                else:
                    quantities = {i["sku"]: i["quantity"] for i in payload["items"]}
                    products = conn.execute(
                        "SELECT * FROM products WHERE sku=ANY(%s) ORDER BY sku FOR UPDATE",
                        (list(quantities),),
                    ).fetchall()
                    if len(products) != len(quantities):
                        raise Problem(422, "INVALID_SKU", "Unknown product")
                    if any(p["available"] < quantities[p["sku"]] for p in products):
                        raise Problem(409, "OUT_OF_STOCK", "Not enough items available")
                    total = sum(
                        p["unit_price_cents"] * quantities[p["sku"]] for p in products
                    )
                    conn.execute(
                        "INSERT INTO orders(id, customer_id, total_cents) VALUES (%s,%s,%s)",
                        (order_id, payload["customer_id"], total),
                    )
                    for p in products:
                        q = quantities[p["sku"]]
                        conn.execute(
                            "UPDATE products SET available=available-%s WHERE sku=%s",
                            (q, p["sku"]),
                        )
                        conn.execute(
                            "INSERT INTO order_items VALUES (%s,%s,%s,%s)",
                            (order_id, p["sku"], q, p["unit_price_cents"]),
                        )
                    conn.execute("INSERT INTO jobs(order_id) VALUES (%s)", (order_id,))
            return {"order_id": str(order_id), "status": "queued"}
        except (psycopg.errors.DeadlockDetected, psycopg.errors.SerializationFailure):
            if attempt == 2:
                raise


@app.post("/api/v1/orders", status_code=202)
async def create_order(request: Request):
    raw = bytearray()
    async for chunk in request.stream():
        raw.extend(chunk)
        if len(raw) > 16 * 1024:
            raise Problem(413, "REQUEST_TOO_LARGE", "Request body exceeds 16 KiB")
    try:
        body = json.loads(raw)
    except (ValueError, UnicodeDecodeError):
        raise Problem(400, "INVALID_JSON", "Body must contain valid JSON") from None
    payload = validate(body, request.headers.get("Idempotency-Key"))
    return await run_in_threadpool(accept, payload, request.headers["Idempotency-Key"])


@app.get("/api/v1/orders/{order_id}")
def get_order(order_id: str):
    try:
        identifier = UUID(order_id)
    except ValueError:
        raise Problem(404, "ORDER_NOT_FOUND", "Order not found") from None
    with connect() as conn:
        row = conn.execute(
            "SELECT id, status, total_cents FROM orders WHERE id=%s", (identifier,)
        ).fetchone()
    if not row:
        raise Problem(404, "ORDER_NOT_FOUND", "Order not found")
    return {
        "order_id": str(row["id"]),
        "status": row["status"],
        "total_cents": row["total_cents"],
    }


@app.get("/metrics")
def metrics():
    with connect() as conn:
        counts = conn.execute("""SELECT
            (SELECT count(*) FROM orders) AS created,
            (SELECT count(*) FROM orders WHERE status='failed') AS failed,
            (SELECT coalesce(sum(greatest(attempts-1,0)),0) FROM jobs) AS retries""").fetchone()
    text = generate_latest(registry).decode()
    for name, value in counts.items():
        full = {
            "created": "fulfillops_orders_created_total",
            "failed": "fulfillops_orders_failed_total",
            "retries": "fulfillops_worker_retries_total",
        }[name]
        text += f"# TYPE {full} counter\n{full} {value}\n"
    return Response(text, media_type="text/plain; version=0.0.4")
