import psycopg
from psycopg import sql

from common.config import settings
from common.database import connect
from db.manage import migrate, seed


def provision():
    env = settings()
    with connect() as conn:
        for role, password_key in [
            ("fulfillops_api", "API_DB_PASSWORD"),
            ("fulfillops_worker", "WORKER_DB_PASSWORD"),
        ]:
            password = env.get(password_key)
            if not password:
                raise RuntimeError("Runtime database passwords are required")
            exists = conn.execute(
                "SELECT 1 FROM pg_roles WHERE rolname=%s", (role,)
            ).fetchone()
            if not exists:
                conn.execute(
                    sql.SQL("CREATE ROLE {} LOGIN").format(sql.Identifier(role))
                )
            conn.execute(
                sql.SQL("ALTER ROLE {} PASSWORD {}").format(
                    sql.Identifier(role), sql.Literal(password)
                )
            )
            conn.execute(
                sql.SQL("GRANT USAGE ON SCHEMA public TO {}").format(
                    sql.Identifier(role)
                )
            )
            conn.execute(
                sql.SQL("GRANT SELECT ON schema_migrations TO {}").format(
                    sql.Identifier(role)
                )
            )
        conn.execute(
            "GRANT SELECT ON products, orders, jobs, order_requests TO fulfillops_api"
        )
        conn.execute(
            "GRANT INSERT ON orders, order_requests, order_items, jobs TO fulfillops_api"
        )
        conn.execute("GRANT UPDATE (available) ON products TO fulfillops_api")
        conn.execute("GRANT SELECT, UPDATE ON orders, jobs TO fulfillops_worker")
        conn.execute(
            "GRANT SELECT, INSERT, UPDATE ON job_attempts TO fulfillops_worker"
        )
        conn.execute("GRANT SELECT, INSERT ON completion_receipts TO fulfillops_worker")
    print("Runtime roles provisioned")


if __name__ == "__main__":
    try:
        migrate()
        if settings().get("APP_ENV") == "test":
            seed()
        provision()
    except (psycopg.Error, RuntimeError):
        raise SystemExit(
            "Bootstrap failed; check connectivity, migration state and local configuration"
        ) from None
