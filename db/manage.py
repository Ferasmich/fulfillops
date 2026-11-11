import argparse
import hashlib

import psycopg

from common.config import ROOT, settings
from common.database import connect

MIGRATIONS = ROOT / "db" / "migrations"
CATALOG = [("KIT-100", 1299, 7), ("PART-200", 599, 12), ("PACK-300", 249, 5)]


def migration_files():
    return sorted(MIGRATIONS.glob("[0-9]*.sql"))


def migrate():
    with connect() as conn:
        conn.execute("SELECT pg_advisory_xact_lock(73195001)")
        conn.execute("""CREATE TABLE IF NOT EXISTS schema_migrations (
            version TEXT PRIMARY KEY, checksum TEXT NOT NULL,
            applied_at TIMESTAMPTZ NOT NULL DEFAULT clock_timestamp())""")
        applied = {
            row["version"]: row["checksum"]
            for row in conn.execute("SELECT version, checksum FROM schema_migrations")
        }
        for file in migration_files():
            checksum = hashlib.sha256(file.read_bytes()).hexdigest()
            if file.name in applied:
                if applied[file.name] != checksum:
                    raise RuntimeError("Applied migration changed: " + file.name)
                print("Already applied:", file.name)
                continue
            conn.execute(file.read_text())
            conn.execute(
                "INSERT INTO schema_migrations VALUES (%s, %s, DEFAULT)",
                (file.name, checksum),
            )
            print("Applied:", file.name)
    print("Migrations committed")


def test_target():
    env = settings()
    if (
        env.get("APP_ENV") != "test"
        or not env.get("POSTGRES_DB", "").startswith("fulfillops_test")
        or env.get("DB_HOST", "127.0.0.1") not in ("127.0.0.1", "localhost", "db")
    ):
        raise RuntimeError(
            "Refusing operation: requires APP_ENV=test and an allowlisted local/Compose fulfillops_test database"
        )


def seed():
    test_target()
    with connect() as conn, conn.cursor() as cur:
        cur.executemany(
            """INSERT INTO products VALUES (%s, %s, %s)
                ON CONFLICT (sku) DO NOTHING""",
            CATALOG,
        )
    print("Test catalog seeded; existing stock was not changed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["migrate", "seed", "reset-test"])
    parser.add_argument("--confirm-test-reset", action="store_true")
    args = parser.parse_args()
    try:
        if args.command == "migrate":
            migrate()
        elif args.command == "seed":
            seed()
        else:
            test_target()
            if not args.confirm_test_reset:
                raise RuntimeError("Explicit test-reset confirmation required")
            with connect() as conn:
                conn.execute(
                    "TRUNCATE products, orders, order_requests, order_items, jobs, job_attempts, completion_receipts CASCADE"
                )
            seed()
    except (psycopg.Error, RuntimeError):
        raise SystemExit(
            "Database operation failed. Check connectivity, migration history and test-target settings."
        ) from None
