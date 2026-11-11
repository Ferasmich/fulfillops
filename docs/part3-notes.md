# Part 3 — Durable worker

## How it works

The API stores a job in the same transaction as the accepted order and stock reservation. A separate worker polls that work table. `FOR UPDATE SKIP LOCKED` lets two workers claim different available jobs without waiting on each other's claimed row.

A claim records a unique token, increments the persistent attempt count and gives the worker a lease. Processing happens outside that short claim transaction. Before completion, the worker locks the job again and checks its token and lease using database time. The completion receipt, order status and job status commit together. A unique receipt per order prevents a second database completion effect.

If a worker dies, its job stays stored. Once the lease expires, another worker records the interrupted attempt and claims the job with a new token. The old token cannot complete or fail the newly owned job.

Processing failures use bounded exponential backoff. The normal maximum is five attempts. Exhausted jobs become failed and stay available for operator review. Inventory is not restored automatically. Even a crash during the last allowed attempt eventually becomes failed rather than looping forever.

## What was tested

The combined suite passed 34 tests. The supplied checker passed all 15 checks with both concurrency and stress enabled, with no skipped checks.

- Two workers completed one order with one receipt and one stock decrement.
- Worker 14947 was killed after claiming order `8405e2ed-56ed-410a-bb8a-e5e4753649bb`. Worker 14948 recovered it: attempt 1 became lease_expired, attempt 2 completed. There was one receipt and stock stayed at six.
- Poison order `dddf3673-5e38-45cf-a17a-61e467248245` used a test-specific three-attempt limit. Its history was retry, retry, failed. It had no completion receipt and kept the reserved stock. Further polling did not increase attempts.
- A stale worker could neither complete nor fail a job after another claim took ownership.
- An expired final attempt became failed without another attempt.
- A persisted retry delay prevented immediate reclamation.

See `evid/03-worker/` for raw results, process IDs and timestamped worker logs. The drill uses shortened leases and backoff in a fresh disposable database. It does not erase the working database or contact external systems.

## Questions to prepare for

- **Why not remove a job when a worker picks it up?** A crash would lose the only record of pending work.
- **What is a lease?** A time-limited right to process a job. When it expires, another worker may recover it.
- **Why a token too?** An old worker might resume after expiry. Its old token must not overwrite the new owner's result.
- **Is delivery exactly once?** No. A job may run again after a crash. The protected database completion effect happens once.
- **Why not restore stock on failure?** The contract requires manual reconciliation and avoids silently making reserved stock available again.
- **How do retries stop?** Each claim increments a stored count. The maximum is checked on errors and expired-claim recovery.
- **What if the database fails during completion?** The transaction either commits or rolls back; persisted state/lease enables recovery. No external outcome is triggered by this lab worker.
- **Why not hold a database lock throughout processing?** Long processing should not hold an open transaction. The short claim plus fenced completion protects the outcome.

## Limits and next work

Completion is a short simulated database operation. There is no lease renewal for long-running work; jobs exceeding the configured lease lose ownership and may eventually fail. Real external effects would need their own idempotency protocol. Production worker permissions, container/cluster deployment, monitoring measurements and GitOps remain later work. Operator review currently means inspecting stored orders/jobs/attempts; there is no automatic redrive or restocking tool.

One upstream TestClient/HTTPX deprecation warning remains in the passing test output. Part 4 still needs its deliberate regression fail-to-pass demonstration and the full test strategy.
