# Test strategy

The project uses pytest. Tests check business rules first, then the API/database together, then concurrent processes and failure recovery. The supplied checker is an extra contract check, not a replacement for the owned tests.

| Layer | Location | What it checks | Needs PostgreSQL? |
|---|---|---|---|
| Unit: 34 cases | `tests/unit/` | Quantity types/bounds, customer/key bounds, normalization and duplicate-line aggregation | No |
| API integration: 26 cases | `tests/integration/test_api.py` | Responses, totals, transactions, replay, migrations, readiness and restart persistence | Yes |
| Worker/checker: seven cases | `tests/integration/test_worker.py` | Two workers, crash recovery, poison attempts, stale ownership, backoff and supplied checker | Yes |
| Concurrency: two cases | `tests/races/test_orders.py` | Same keys and different keys across two real API processes | Yes |

## Run locally

Activate `.venv` and keep Docker's database service running.

```bash
python -m pytest tests/unit -v
python -m pytest tests/integration -v
python -m pytest tests/races -v -s
python -m pytest -v --junitxml=evid/04-tests/test-results.xml
ruff check api common db worker tests scripts/regression_demo.py
```

Integration/race tests create a separate randomly named test database and drop it afterwards. The existing working database is not reset. Unit tests skip database setup entirely. Do not use pytest-xdist yet: cases currently share one disposable database and clear its contents between tests.

For a full run that also saves new worker/checker logs beside the Part 4 results:

```bash
FULFILLOPS_EVIDENCE_DIR=evid/04-tests/worker python -m pytest -v -s --junitxml=evid/04-tests/test-results.xml
```

## Race tests

Each race uses a barrier so clients start the requests together. Requests are explicitly split across two independently running Uvicorn processes using the same PostgreSQL database.

- Same key: eight requests, four per process. Expect eight accepted receipts with one order ID, one persisted order/job/key and one stock decrement.
- Different keys: twelve requests, six per process, competing for seven KIT-100 units. Expect seven unique accepted orders, five OUT_OF_STOCK responses and zero remaining stock.

The tests print process IDs and query the database to check the outcome. Race tests demonstrate the observed runs; they do not prove all possible schedules. Database locks and constraints are the mechanism that enforces the invariant.

## Deliberate failure and repair

```bash
python scripts/regression_demo.py
```

The script copies the necessary application code and one regression test into a temporary directory. In that copy it changes the strict integer check to `isinstance(quantity, int)`. Python treats booleans as integers for that check, so quantity `true` is accepted and the regression test fails.

It then restores the correct strict type check in the copy and reruns the same test, which passes. The script verifies the expected exit codes and saves both outputs. It never edits the running application's source or accesses the database.

This is a deliberate local regression exercise, not an observed production defect or a red-to-green CI pipeline. The separate CI demonstration remains to be done in Part 6.

## Results and limits

Part 4 saved run: 52 passed. Part 5 added six test-target guard cases; the latest full run in `evid/05-containers/` has 58 passed, plus the container checker reporting 15 passed / 0 failed / 0 skipped. Ruff passed. JUnit XML is saved for machine-readable reporting; the CI upload will be added with GitHub Actions. There is one upstream TestClient/HTTPX deprecation warning in the output. These checks do not cover container hardening, Kubernetes, GitOps or production performance.

Part 6 adds 11 security-policy unit cases. Latest local full suite: 69 passed, recorded in `evid/06-ci/local-tests.txt`; live CI execution remains pending.
