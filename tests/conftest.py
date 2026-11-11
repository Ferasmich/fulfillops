import os
from uuid import uuid4

import pytest
from psycopg import sql

from common.database import connect
from db.manage import migrate, seed


@pytest.fixture(scope="session")
def isolated_database():
    name = "fulfillops_test_part2_" + uuid4().hex[:12]
    previous = os.environ.get("POSTGRES_DB")
    previous_env = os.environ.get("APP_ENV")
    with connect(dbname="postgres", autocommit=True) as conn:
        conn.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
    os.environ["POSTGRES_DB"] = name
    os.environ["APP_ENV"] = "test"
    try:
        migrate()
        yield name
    finally:
        with connect(dbname="postgres", autocommit=True) as conn:
            conn.execute(
                sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(name))
            )
        if previous is None:
            os.environ.pop("POSTGRES_DB", None)
        else:
            os.environ["POSTGRES_DB"] = previous
        if previous_env is None:
            os.environ.pop("APP_ENV", None)
        else:
            os.environ["APP_ENV"] = previous_env


@pytest.fixture(autouse=True)
def fresh_catalog(request):
    if "unit" in request.node.path.parts:
        return
    isolated_database = request.getfixturevalue("isolated_database")
    assert os.environ["POSTGRES_DB"] == isolated_database
    assert isolated_database.startswith("fulfillops_test_part2_")
    with connect() as conn:
        conn.execute(
            "TRUNCATE products, orders, order_requests, order_items, jobs, job_attempts, completion_receipts CASCADE"
        )
    seed()
