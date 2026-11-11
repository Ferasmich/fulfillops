# Migrations

Run `python -m db.manage migrate` from the project root with the virtual environment active.

- `001_products.sql`: product catalog and stock constraints.
- `002_orders.sql`: orders, items and unique idempotency mappings.
- `003_jobs.sql`: durable work and the tables needed for later worker recovery.

The runner takes a database advisory lock, checks existing versions/checksums, applies pending files and commits them together. Rerunning skips applied versions. Do not edit an applied migration or execute files manually; add a new numbered file for a new change. A database with manually created tables needs explicit reconciliation, not silent history adoption.

Seeds are separate: `APP_ENV=test python -m db.manage seed`. There is no general reset command yet.
