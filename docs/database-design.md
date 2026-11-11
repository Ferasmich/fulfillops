# Database design

Status: implemented by migrations 001–003 and verified in Part 2. This document explains the design; test results are in `evid/02-api/`. Worker processing and recovery were added and tested in Part 3; see `evid/03-worker/`.

| Table | Fields and constraints |
|---|---|
| schema_migrations | version primary key, checksum, applied_at; required version checked by readiness |
| products | sku text primary key; unit_price_cents integer > 0; available integer >= 0 |
| orders | id UUID primary key; customer_id text length 1–64; status in queued/processing/completed/failed; total_cents bigint >= 0; created_at, completed_at |
| order_requests | key text primary key with 8–128 printable-ASCII validation; canonical_payload jsonb not null; order_id UUID unique FK to orders DEFERRABLE INITIALLY DEFERRED; created_at |
| order_items | order_id FK; sku FK; primary key (order_id, sku); quantity integer > 0; unit_price_cents integer > 0; aggregated lines and acceptance-time price snapshot |
| jobs | order_id UUID primary key/FK; state queued/processing/completed/failed; attempts integer >= 0; max_attempts integer > 0; attempts <= max_attempts; available_at; lease_until; claim_token UUID; last_error_code; updated_at |
| job_attempts | order_id FK; attempt_number; primary key (order_id, attempt_number); unique claim_token; started_at, ended_at; outcome claimed/completed/retry/failed/lease_expired; safe error category |
| completion_receipts | order_id primary key/FK; completed_at; represents the single persisted completion effect |

Use timestamptz and database time for leases. Index due queued jobs by available_at and expired processing jobs by lease_until. Add ownership consistency checks: processing requires a token/lease; non-processing rows have neither. Validate cross-table status transitions in transactional application SQL and integration tests; foreign keys alone do not enforce them.

Original per-line quantity is 1–20 and line count 1–10. Aggregated quantity may be up to 200; do not apply the original per-line maximum to an aggregated row. Price totals use integers only and are calculated from snapshots. Check total equals item sums in integration tests.

Migrations run explicitly before services become ready, never independently from every replica. Use a transaction-scoped advisory lock in the migration runner to serialize competing invocations. Store migration checksums and reject edited applied versions.

Seed the three fixed products only through an explicit fresh-dataset step. Never overwrite existing available counts during startup, migration or replay. A test reset needs an explicit test environment marker, dedicated test database name and an allowlisted connection target. Refuse unknown/non-test targets and do not provide reset through HTTP.

Use a privileged migration role separately from runtime roles. API needs product reads/reservation writes, order/key/item/job creation and order reads. Worker needs job/attempt/order/receipt operations, not product updates. Provision roles and secrets outside committed values. Exact grants will be verified during runtime implementation.
