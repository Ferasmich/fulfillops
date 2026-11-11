# Part 2 — API and database

These notes describe the Part 2 milestone. The worker and full checker were subsequently completed in Part 3; see `part3-notes.md`.

## What was built

The API validates requests, reserves inventory and creates queued orders. PostgreSQL stores the order, item prices, idempotency key and pending job in one transaction. The HTTP response is returned after commit.

The database row locks stop different requests from reserving the same remaining stock. Rows are locked in SKU order. A unique idempotency key prevents duplicate accepted orders across API processes. Replays compare normalized customer/items and return the original ID, including a queued acceptance receipt when an order is already completed.

Migrations are tracked in `schema_migrations`. Repeating the migration command skips existing versions, and an edited applied file is rejected. Seeding is separate and does not reset inventory.

## Results

27 integration cases passed against a separate disposable PostgreSQL database. Ruff passed. The saved results are in `evid/02-api/`.

- Same-key replay created one order and one job; KIT-100 stock went from 7 to 6 once.
- Eight synchronized same-key requests reached two API processes and returned one order ID.
- Twelve competing requests then took the remaining six units: six accepted, six rejected, final stock zero.
- After restarting an API process, replay still returned the same order ID and stock remained six.
- An order with one insufficient item rolled back every reservation and left no order, key or job.
- Duplicate SKU lines were aggregated correctly. One KIT-100 plus two PART-200 units totalled 2497 cents.
- Invalid quantities, including booleans, were rejected. Oversized streamed bodies were rejected.
- Readiness failed with unavailable storage while liveness stayed healthy.
- Migration reruns and reseeding did not restore consumed stock.

## Limits

There is no worker yet. Accepted orders remain queued. The completed-receipt test changes order state as a test fixture; it does not prove worker processing. The full supplied checker has not been run because it expects completion. Crash/poison recovery, CI, application containers, GitOps and operational measurements remain later work.

Pytest reports one upstream TestClient/HTTPX deprecation warning; the tests pass. HTTP metrics are per API process; database business counts are global and must not be summed once per replica. The retry metric is zero until worker attempts exist. The local development database role is privileged; separate runtime permissions still need hardening.

## Questions to prepare for

- **Why a transaction?** Stock, order, idempotency mapping and job must either all commit or all roll back.
- **Why not check stock and update later?** Two requests could both read the last unit before either reserves it.
- **Why a unique key in the database?** A Python variable or lock cannot coordinate separate API processes or survive restarts.
- **Why a deferred foreign key?** The request-key row is inserted first as the uniqueness gate; its order must exist before commit.
- **Why return queued on replay after completion?** The POST response is the acceptance receipt. GET order returns the current state.
- **Why migrations rather than CREATE TABLE on startup?** They track changes explicitly and let replicas share a known schema.
- **Why does seeding not restore stock?** Restarting or seeding must not undo accepted orders.
- **Why no worker in the API handler?** Acceptance is fast and durable; a separate process will finish jobs asynchronously.
