# FulfillOps

An order API with PostgreSQL inventory reservations and persistent idempotency. The API and separate worker work locally. Accepted orders are reserved immediately and completed asynchronously.

## Run the complete stack with Docker

Keep `.env` local. It needs `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `API_DB_PASSWORD` and `WORKER_DB_PASSWORD`; see `.env.example`. Separate runtime passwords were generated locally where missing. Stop manually running API/workers before using their container versions.

```bash
docker compose up -d --build
docker compose ps --all
```

The database starts first. Init applies pending migrations, seeds missing products only in test mode and grants runtime roles, then exits with code 0. The API and two workers start afterwards. API: localhost:8080; database: localhost:5433. `API_PORT` and `POSTGRES_PORT` can override host ports.

```bash
docker compose down
```

This keeps the database volume. Restarting does not restore spent stock. Logs: `docker compose logs api worker`. The API/workers run non-root with read-only filesystems and separate restricted database roles.

```bash
python -m scripts.verify_containers
```

With development dependencies installed, this repeats the clean builds, image-size comparison, health/user/privilege checks, full checker, shutdown/startup persistence and guarded test-reset exercise. It uses a uniquely named private test stack/volume and removes only those resources afterwards. [Part 5 evidence](evid/05-containers/README.md).

To deliberately reset the working test dataset, stop its application processes first:

```bash
docker compose stop api worker
docker compose run --rm --no-deps init python -m db.manage reset-test --confirm-test-reset
docker compose up -d
```

This deletes test orders and restores stock. It refuses non-test settings, non-test database names, unapproved hosts and missing confirmation. It is not part of normal startup.

On 11 November Docker created a fresh default database volume because the previous one was absent. Earlier manual-order responses remain saved as historical evidence; those old orders are not claimed to exist in the new volume.

## Run directly from Python

Keep only the database container running for this mode: `docker compose stop api worker`. Use Python 3.12 and open a terminal in this folder.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements/development.txt
```

Create `.env` from `.env.example` and set your local database password. If you already have `.env`, keep it. Do not commit it. The API loads this file directly; environment variables take priority.

```bash
docker compose up -d db
python -m db.manage migrate
APP_ENV=test python -m db.manage seed
python -m uvicorn api.main:app --host 127.0.0.1 --port 8080
```

The migration command applies only new SQL files, records checksums and refuses changed applied files. Seeding requires a local database whose name starts with `fulfillops_test`; it adds missing products without restoring spent stock. Do not apply numbered SQL files manually: the runner records migration history.

The default connection is localhost port 5433. Database credentials come from `.env`; no password belongs in source code. This local setup currently uses the development database role. Compose now uses separate restricted runtime roles; direct Python development commands still use the owner role.

## Start the workers

Keep the API running. In each of two additional terminals, activate `.venv` and run:

```bash
python -m worker.main
```

Both workers use the same database. A worker claims a job with a token and a ten-second lease. A crashed job can be reclaimed after expiry. Normal jobs finish quickly; this implementation models completion as a database receipt, not an external shipping/payment call. A live worker that exceeds its lease cannot commit a stale result.

Default retry limit is five attempts, with 1/2/4/8-second delays before later attempts. Failed orders remain stored with their stock reserved for manual review. Stop a worker with Ctrl+C; it finishes its current short operation and exits. A hard kill is recovered through lease expiry.

## Try an order

In a second terminal:

```bash
curl http://localhost:8080/health/ready
curl http://localhost:8080/api/v1/catalog
curl -i http://localhost:8080/api/v1/orders \
  -H 'Content-Type: application/json' \
  -H 'Idempotency-Key: example-order-001' \
  -d '{"customer_id":"CUST-042","items":[{"sku":"KIT-100","quantity":1}]}'
```

Run that same POST again: the order ID should stay the same and stock should decrease only once. These example requests consume test stock. Use the returned ID with `GET /api/v1/orders/{order_id}` to check the total and status. `/metrics` exposes HTTP counters, latency and database-backed business counts.

## Tests

```bash
python -m pytest -v
ruff check api common db worker tests scripts
```

Tests create a separate uniquely named database, seed it, and remove that database afterwards. They do not reset `fulfillops_test`. The local development role needs CREATE DATABASE permission for this test setup. Two tests use real API subprocesses to verify restart persistence and concurrent requests across two replicas.

Results: [Part 2 evidence](evid/02-api/README.md) and [Part 3 evidence](evid/03-worker/README.md). Current combined results: 69 tests passed; supplied checker with both flags: 15 passed / 0 failed / 0 skipped.

To repeat the worker crash/poison drills and checker safely:

```bash
python -m pytest tests/integration/test_worker.py -v -s
```

This creates a fresh disposable database, runs two workers and an API, injects faults, saves results under `evid/03-worker/`, and cleans up its own processes/database. It does not reset the working dataset. The poison fixture uses a specific order ID and refuses non-test/nonlocal targets. Test timing values are shortened for quick recovery; default worker lease is ten seconds.

For the supplied checker alone, use `assessment/fulfillops_public_checker.py --concurrency --stress` against a fresh isolated stack with its API and workers running. Do not use a spent working dataset and expect all checks to run.

## Test strategy and regression demo

See [test strategy](docs/test-strategy.md) for unit/integration/race commands. [Part 4 evidence](evid/04-tests/README.md) contains the results and required failing/fixed demonstration.

```bash
python scripts/regression_demo.py
```

The deliberate bug is introduced only in a temporary code copy; the working API is not modified. CI red-to-green proof is still pending.

## Stop

Stop the API and both workers with Ctrl+C. Stop the database with `docker compose down`; the volume keeps its data. Do not add `-v` unless you intentionally want to destroy that local volume.

## CI and image publication

[The workflow](.github/workflows/ci.yml) checks PRs/pushes to main. It runs tests, builds/checks the image, generates an SBOM and enforces the [security policy](docs/security-policy.md). Publication is a separate manual dispatch on main with `publish=true`, and only runs after all quality checks pass. It promotes the accepted image archive instead of rebuilding.

Local verification: [Part 6 evidence](evid/06-ci/README.md). Live runs, CI artifacts and the published digest are still pending the initial commit/push and release approval. The current scan has unfixed High/Critical findings; a passing policy gate does not mean no vulnerabilities.

```bash
python -m scripts.ci_stack
python -m scripts.scan_image --image fulfillops:local --output evid/06-ci
```

The first command requires the local image and database settings and starts only a private disposable test stack. The second scans a saved image without exposing the Docker socket or local credentials to the scanner.

## Notes and design

- [Project plan](Project%20Implementation.md)
- [Architecture](docs/architecture.md) and [ADR](docs/ADR-001.md)
- [Database](docs/database-design.md) and [threat model](docs/threat-model.md)
- [Evidence checklist](evid/INDEX.md)
- [Part 2 report notes and defense questions](docs/part2-notes.md)
- [Part 3 report notes and defense questions](docs/part3-notes.md)
- [Part 4 report notes and defense questions](docs/part4-notes.md)
- [Part 5 report notes and defense questions](docs/part5-notes.md)
- [Part 6 report notes and defense questions](docs/part6-notes.md)
- [Assistance log](docs/assistance-log.md)

The original source pack is kept locally in `FulfillOps_9_5_STUDENTS_COMPLETE/` and excluded from Git; unchanged text/checker copies are in `assessment/`. The assignment specifies teams of 2–3; solo assessment approval remains unverified. No commits or pushes have been made.
