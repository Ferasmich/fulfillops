# Worker and recovery evidence

Run on 10 November 2026, against a fresh isolated PostgreSQL database.

- [Combined test output](test-results.txt): Ruff passed, 34 integration cases passed (27 API and seven worker/checker cases).
- [JUnit output](test-results.xml).
- [Supplied public checker](public-checker.txt): `--concurrency --stress`, **15 passed / 0 failed / 0 skipped**.
- [Killed worker](crash-victim.log) and [recovering worker](crash-survivor.log): timestamped claim/recovery logs. Exact process IDs and final database assertions appear in test output.
- [Poison worker A](poison-a.log) and [poison worker B](poison-b.log): bounded retries with a three-attempt lab limit. The test output shows failed state, attempts and retained stock.
- [Checker worker A](checker-a.log) and [checker worker B](checker-b.log): workers running during the checker.

Reproduce the fault drills and checker: `python -m pytest tests/integration/test_worker.py -v -s`. This is the reproducible fault-injection procedure; the test deliberately kills only its own subprocess and removes only its own temporary database. Individual logs are refreshed when these tests run again. The summary above describes the saved final run; prior Part 2 results remain in `evid/02-api/`.

Tests use a 0.5-second lease and short retry delays; normal defaults are a ten-second lease, five attempts and exponential backoff starting at one second. Completed means a single durable database receipt, not an external business operation. TestClient emitted one upstream deprecation warning; all checks passed.

- [Manual order example](manual-order.txt): owner-supplied acceptance and completed lookup responses for the same order, total 1299 cents.
