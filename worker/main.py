import json
import signal
import time
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import psycopg

from common.config import settings
from common.database import connect
from db.manage import test_target


def log(event, order_id=None, **fields):
    print(
        json.dumps(
            {
                "time": datetime.now(UTC).isoformat(),
                "event": event,
                "order_id": str(order_id) if order_id else None,
                **fields,
            }
        ),
        flush=True,
    )


def claim(lease_seconds=10):
    with connect() as conn:
        job = conn.execute("""SELECT * FROM jobs WHERE
            (state='queued' AND available_at <= clock_timestamp()) OR
            (state='processing' AND lease_until <= clock_timestamp())
            ORDER BY available_at, order_id FOR UPDATE SKIP LOCKED LIMIT 1""").fetchone()
        if job is None:
            return None
        if job["state"] == "processing":
            conn.execute(
                """UPDATE job_attempts SET ended_at=clock_timestamp(),
                outcome='lease_expired', error_code='WORKER_INTERRUPTED'
                WHERE order_id=%s AND attempt_number=%s AND outcome='claimed'""",
                (job["order_id"], job["attempts"]),
            )
        if job["attempts"] >= job["max_attempts"]:
            conn.execute(
                """UPDATE jobs SET state='failed', claim_token=NULL,
                lease_until=NULL, last_error_code='ATTEMPTS_EXHAUSTED', updated_at=clock_timestamp()
                WHERE order_id=%s""",
                (job["order_id"],),
            )
            conn.execute(
                "UPDATE orders SET status='failed' WHERE id=%s", (job["order_id"],)
            )
            return None
        token = uuid4()
        job = conn.execute(
            """UPDATE jobs SET state='processing', attempts=attempts+1,
            claim_token=%s, lease_until=clock_timestamp()+make_interval(secs => %s),
            updated_at=clock_timestamp() WHERE order_id=%s RETURNING *""",
            (token, lease_seconds, job["order_id"]),
        ).fetchone()
        conn.execute(
            "UPDATE orders SET status='processing' WHERE id=%s", (job["order_id"],)
        )
        conn.execute(
            """INSERT INTO job_attempts(order_id, attempt_number, claim_token, outcome)
            VALUES (%s,%s,%s,'claimed')""",
            (job["order_id"], job["attempts"], token),
        )
    return job


def owns(conn, job):
    row = conn.execute(
        "SELECT state, claim_token FROM jobs WHERE order_id=%s FOR UPDATE",
        (job["order_id"],),
    ).fetchone()
    if (
        not row
        or row["state"] != "processing"
        or row["claim_token"] != job["claim_token"]
    ):
        return False
    # Read database time after acquiring the lock, even if lock acquisition waited.
    return conn.execute(
        "SELECT lease_until > clock_timestamp() AS valid FROM jobs WHERE order_id=%s",
        (job["order_id"],),
    ).fetchone()["valid"]


def complete(job):
    with connect() as conn:
        if not owns(conn, job):
            return False
        conn.execute(
            "INSERT INTO completion_receipts(order_id) VALUES (%s) ON CONFLICT DO NOTHING",
            (job["order_id"],),
        )
        conn.execute(
            """UPDATE jobs SET state='completed', claim_token=NULL,
            lease_until=NULL, last_error_code=NULL, updated_at=clock_timestamp() WHERE order_id=%s""",
            (job["order_id"],),
        )
        conn.execute(
            "UPDATE orders SET status='completed', completed_at=clock_timestamp() WHERE id=%s",
            (job["order_id"],),
        )
        conn.execute(
            """UPDATE job_attempts SET outcome='completed', ended_at=clock_timestamp()
            WHERE order_id=%s AND attempt_number=%s""",
            (job["order_id"], job["attempts"]),
        )
    return True


def fail(job, retry_base=1):
    with connect() as conn:
        if not owns(conn, job):
            return False
        terminal = job["attempts"] >= job["max_attempts"]
        state = "failed" if terminal else "queued"
        delay = min(retry_base * 2 ** min(job["attempts"] - 1, 10), 60)
        conn.execute(
            """UPDATE jobs SET state=%s, claim_token=NULL, lease_until=NULL,
            last_error_code='PROCESSING_ERROR', available_at=clock_timestamp()+make_interval(secs => %s),
            updated_at=clock_timestamp() WHERE order_id=%s""",
            (state, delay, job["order_id"]),
        )
        conn.execute(
            "UPDATE orders SET status=%s WHERE id=%s", (state, job["order_id"])
        )
        conn.execute(
            """UPDATE job_attempts SET outcome=%s, error_code='PROCESSING_ERROR',
            ended_at=clock_timestamp() WHERE order_id=%s AND attempt_number=%s""",
            ("failed" if terminal else "retry", job["order_id"], job["attempts"]),
        )
    return True


class ProcessingFailure(Exception):
    pass


def run():
    env = settings()
    poison = env.get("WORKER_TEST_POISON_ORDER_ID")
    if poison:
        test_target()
    delay = float(env.get("WORKER_PROCESS_SECONDS", "0.05"))
    lease = float(env.get("WORKER_LEASE_SECONDS", "10"))
    poll = float(env.get("WORKER_POLL_SECONDS", "1"))
    backoff = float(env.get("WORKER_RETRY_BASE_SECONDS", "1"))
    if min(lease, poll, backoff) <= 0 or delay < 0:
        raise SystemExit(
            "Worker timing values must be positive (processing delay may be zero)"
        )
    stopping = False

    def stop(signum, frame):
        nonlocal stopping
        stopping = True

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    log("worker_started")
    while not stopping:
        Path("/tmp/fulfillops-worker-heartbeat").touch()
        try:
            job = claim(lease)
            if job is None:
                time.sleep(poll)
                continue
            log("claimed", job["order_id"], attempt=job["attempts"])
            time.sleep(delay)
            try:
                if str(job["order_id"]) == poison:
                    raise ProcessingFailure()
                applied = complete(job)
                log("completed" if applied else "ownership_lost", job["order_id"])
            except ProcessingFailure:
                applied = fail(job, backoff)
                log(
                    "processing_failed" if applied else "ownership_lost",
                    job["order_id"],
                    attempt=job["attempts"],
                )
        except psycopg.Error:
            # Do not log database messages or connection strings. The lease permits recovery.
            log("storage_unavailable")
            time.sleep(poll)
    log("worker_stopped")


if __name__ == "__main__":
    run()
