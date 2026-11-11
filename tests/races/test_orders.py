from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import httpx

from common.database import connect
from tests.helpers import server


def race(urls, keys):
    barrier = Barrier(len(keys))

    def submit(pair):
        url, key = pair
        barrier.wait(timeout=15)
        return httpx.post(
            url + "/api/v1/orders",
            json={
                "customer_id": "CUST-RACE",
                "items": [{"sku": "KIT-100", "quantity": 1}],
            },
            headers={"Idempotency-Key": key},
            timeout=15,
        )

    with ThreadPoolExecutor(max_workers=len(keys)) as pool:
        return list(
            pool.map(submit, [(urls[i % len(urls)], key) for i, key in enumerate(keys)])
        )


def database_state():
    with connect() as conn:
        return conn.execute("""SELECT
            (SELECT available FROM products WHERE sku='KIT-100') AS stock,
            (SELECT count(*) FROM orders) AS orders,
            (SELECT count(*) FROM jobs) AS jobs,
            (SELECT count(*) FROM order_requests) AS keys""").fetchone()


def test_same_key_across_two_api_processes():
    with server() as (a, pid_a), server() as (b, pid_b):
        responses = race([a, b], ["same-key-race-001"] * 8)
        assert all(r.status_code == 202 for r in responses)
        ids = {r.json()["order_id"] for r in responses}
        assert len(ids) == 1
        state = database_state()
        assert state == {"stock": 6, "orders": 1, "jobs": 1, "keys": 1}
        print(
            f"Same-key race: API PIDs {pid_a}/{pid_b}; four calls per API; eight 202 responses; IDs {ids}; SQL snapshot {state}"
        )


def test_distinct_keys_cannot_oversell_across_two_api_processes():
    with server() as (a, pid_a), server() as (b, pid_b):
        responses = race([a, b], [f"distinct-race-{i:03}" for i in range(12)])
        accepted = [r for r in responses if r.status_code == 202]
        rejected = [r for r in responses if r.status_code == 409]
        assert len(accepted) == 7
        assert len({r.json()["order_id"] for r in accepted}) == 7
        assert len(rejected) == 5
        assert all(r.json()["error"]["code"] == "OUT_OF_STOCK" for r in rejected)
        state = database_state()
        assert state == {"stock": 0, "orders": 7, "jobs": 7, "keys": 7}
        print(
            f"Distinct-key race: API PIDs {pid_a}/{pid_b}; six calls per API; seven accepted, five OUT_OF_STOCK; SQL snapshot {state}"
        )
