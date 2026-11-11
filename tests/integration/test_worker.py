import json
import os
import subprocess
import sys
import time
from contextlib import contextmanager
from datetime import UTC, datetime

from fastapi.testclient import TestClient

from api.main import app
from common.config import ROOT
from common.database import connect
from tests.helpers import server
from worker.main import claim, complete, fail

client = TestClient(app)
EVIDENCE = ROOT / os.environ.get("FULFILLOPS_EVIDENCE_DIR", "evid/03-worker")


def order():
    result = client.post(
        "/api/v1/orders",
        json={"customer_id": "CUST-LAB", "items": [{"sku": "KIT-100", "quantity": 1}]},
        headers={"Idempotency-Key": "worker-order-001"},
    )
    assert result.status_code == 202
    return result.json()["order_id"]


def snapshot(order_id):
    with connect() as conn:
        row = conn.execute(
            """SELECT o.status, j.state, j.attempts,
            (SELECT count(*) FROM completion_receipts WHERE order_id=o.id) AS receipts,
            (SELECT available FROM products WHERE sku='KIT-100') AS stock
            FROM orders o JOIN jobs j ON j.order_id=o.id WHERE o.id=%s""",
            (order_id,),
        ).fetchone()
    return row


def wait_for(predicate, timeout=10):
    until = time.monotonic() + timeout
    while time.monotonic() < until:
        if predicate():
            return
        time.sleep(0.02)
    raise AssertionError("Condition did not become true before timeout")


@contextmanager
def worker(name, **options):
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    env = {
        **os.environ,
        "WORKER_POLL_SECONDS": "0.02",
        "WORKER_LEASE_SECONDS": "0.5",
        "WORKER_RETRY_BASE_SECONDS": "0.05",
        **options,
    }
    with (EVIDENCE / (name + ".log")).open("w") as log:
        process = subprocess.Popen(
            [sys.executable, "-m", "worker.main"],
            cwd=ROOT,
            env=env,
            stdout=log,
            stderr=log,
        )
        try:
            yield process
        finally:
            if process.poll() is None:
                process.terminate()
            process.wait(timeout=10)


def test_two_workers_complete_once():
    order_id = order()
    with worker("normal-a") as a, worker("normal-b") as b:
        wait_for(lambda: snapshot(order_id)["status"] == "completed")
        result = snapshot(order_id)
        assert result == {
            "status": "completed",
            "state": "completed",
            "attempts": 1,
            "receipts": 1,
            "stock": 6,
        }
        print(f"Two workers {a.pid}/{b.pid}; order {order_id}; result {result}")


def test_worker_killed_after_claim_is_recovered():
    order_id = order()
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    timeline = []

    def capture(phase):
        metrics = client.get("/metrics").text
        (EVIDENCE / ("crash-" + phase + ".prom")).write_text(metrics)
        timeline.append(
            {
                "time": datetime.now(UTC).isoformat(),
                "phase": phase,
                "order_id": order_id,
                "state": snapshot(order_id),
                "live": client.get("/health/live").status_code,
                "ready": client.get("/health/ready").status_code,
            }
        )
        return metrics

    assert "fulfillops_worker_retries_total 0" in capture("before")
    with worker("crash-victim", WORKER_PROCESS_SECONDS="5") as victim:
        wait_for(lambda: snapshot(order_id)["state"] == "processing")
        with worker("crash-survivor") as survivor:
            victim.kill()
            victim.wait(timeout=5)
            capture("during")
            print(
                f"Killed worker {victim.pid} after durable claim; survivor {survivor.pid}; order {order_id}"
            )
            wait_for(lambda: snapshot(order_id)["status"] == "completed")
            result = snapshot(order_id)
            assert result["attempts"] == 2
            assert result["receipts"] == 1
            assert result["stock"] == 6
            with connect() as conn:
                attempts = conn.execute(
                    "SELECT attempt_number, outcome FROM job_attempts WHERE order_id=%s ORDER BY attempt_number",
                    (order_id,),
                ).fetchall()
            assert [r["outcome"] for r in attempts] == ["lease_expired", "completed"]
            assert "fulfillops_worker_retries_total 1" in capture("after")
            (EVIDENCE / "worker-crash-timeline.json").write_text(
                json.dumps(timeline, indent=2) + "\n"
            )
            print("Recovery:", result, "attempt history:", attempts)


def test_poison_job_stops_and_keeps_stock():
    order_id = order()
    with connect() as conn:
        conn.execute("UPDATE jobs SET max_attempts=3 WHERE order_id=%s", (order_id,))
    with (
        worker("poison-a", WORKER_TEST_POISON_ORDER_ID=order_id) as a,
        worker("poison-b", WORKER_TEST_POISON_ORDER_ID=order_id) as b,
    ):
        wait_for(lambda: snapshot(order_id)["status"] == "failed")
        before = snapshot(order_id)
        time.sleep(0.2)
        assert snapshot(order_id) == before
        assert before == {
            "status": "failed",
            "state": "failed",
            "attempts": 3,
            "receipts": 0,
            "stock": 6,
        }
        with connect() as conn:
            history = conn.execute(
                "SELECT attempt_number, outcome FROM job_attempts WHERE order_id=%s ORDER BY attempt_number",
                (order_id,),
            ).fetchall()
        assert [r["outcome"] for r in history] == ["retry", "retry", "failed"]
        metrics = client.get("/metrics").text
        assert "fulfillops_orders_failed_total 1" in metrics
        assert "fulfillops_worker_retries_total 2" in metrics
        (EVIDENCE / "poison-after.prom").write_text(metrics)
        print(
            f"Poison job {order_id}; workers {a.pid}/{b.pid}; result {before}; attempts {history}; stable after further polling"
        )


def test_expired_owner_cannot_complete_or_fail():
    order_id = order()
    stale = claim(0.03)
    time.sleep(0.05)
    current = claim(1)
    assert current["claim_token"] != stale["claim_token"]
    assert not complete(stale)
    assert not fail(stale)
    assert complete(current)
    assert not complete(current)
    result = snapshot(order_id)
    assert result["receipts"] == 1
    assert result["attempts"] == 2
    print("Stale claim fenced; current owner completed once:", result)


def test_crash_on_last_attempt_becomes_failed():
    order_id = order()
    with connect() as conn:
        conn.execute("UPDATE jobs SET max_attempts=1 WHERE order_id=%s", (order_id,))
    last = claim(0.03)
    time.sleep(0.05)
    assert claim() is None
    assert not complete(last)
    assert snapshot(order_id) == {
        "status": "failed",
        "state": "failed",
        "attempts": 1,
        "receipts": 0,
        "stock": 6,
    }
    print("Expired final claim persisted as failed without another attempt or restock")


def test_backoff_delays_next_claim():
    order_id = order()
    first = claim()
    assert fail(first, retry_base=2)
    assert claim() is None
    with connect() as conn:
        seconds = conn.execute(
            "SELECT extract(epoch from available_at-clock_timestamp()) AS seconds FROM jobs WHERE order_id=%s",
            (order_id,),
        ).fetchone()["seconds"]
    assert 1 < seconds <= 2
    assert snapshot(order_id)["state"] == "queued"
    print("Retry persisted with approximately two-second backoff")


def test_full_public_checker_with_two_workers():
    with worker("checker-a") as a, worker("checker-b") as b, server() as (url, api_pid):
        command = [
            sys.executable,
            "assessment/fulfillops_public_checker.py",
            "--base-url",
            url,
            "--concurrency",
            "--stress",
        ]
        run = subprocess.run(
            command, check=False, cwd=ROOT, capture_output=True, text=True, timeout=60
        )
        output = (
            "$ python assessment/fulfillops_public_checker.py --base-url "
            + url
            + " --concurrency --stress\n"
            + run.stdout
            + run.stderr
        )
        (EVIDENCE / "public-checker.txt").write_text(
            output + "\nExit code: " + str(run.returncode) + "\n"
        )
        print(f"Full checker: API {api_pid}; workers {a.pid}/{b.pid}\n" + run.stdout)
        assert run.returncode == 0
        assert "15 passed / 0 failed / 0 skipped" in run.stdout
