import psycopg
from psycopg.rows import dict_row

from common.config import settings


def connect(*, dbname=None, autocommit=False):
    env = settings()
    return psycopg.connect(
        host=env.get("DB_HOST", "127.0.0.1"),
        port=env.get("DB_PORT", "5433"),
        dbname=dbname or env.get("POSTGRES_DB", "fulfillops_test"),
        user=env.get("POSTGRES_USER", "fulfillops"),
        password=env.get("POSTGRES_PASSWORD", ""),
        connect_timeout=3,
        options="-c statement_timeout=5000 -c lock_timeout=3000",
        autocommit=autocommit,
        row_factory=dict_row,
    )
