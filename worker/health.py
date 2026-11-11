import time
from pathlib import Path

import psycopg

from common.database import connect


def check():
    try:
        age = time.time() - Path("/tmp/fulfillops-worker-heartbeat").stat().st_mtime
        if age > 15:
            return 1
        with connect() as conn:
            conn.execute("SELECT 1")
    except (OSError, psycopg.Error):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(check())
