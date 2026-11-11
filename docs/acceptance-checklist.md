# Contract and evidence checklist

All items are planned and unchecked. Source: supplied API contract v1.1 and assignment. Test identifiers below are planned owned tests, not existing passing tests.

| ID | Required behavior | Planned verification |
|---|---|---|
| API-01 | live 200 JSON status ok even when DB unavailable | Endpoint test with DB stopped |
| API-02 | ready 200 ready only with reachable DB and applied migrations, otherwise 503 not_ready | DB/migration failure tests |
| API-03 | catalog 200: KIT-100 1299; PART-200 599; PACK-300 249 | Exact fixed catalog test |
| API-04 | inventory 200 with nonnegative JSON integer; unknown SKU 404 SKU_NOT_FOUND | Inventory/type/unknown tests |
| API-05 | missing key 400 IDEMPOTENCY_REQUIRED; key 8–128 printable ASCII | Header boundary tests |
| API-06 | customer_id nonempty string <=64; items array 1–10 objects | Structural tests, 400 INVALID_REQUEST |
| API-07 | invalid JSON 400 INVALID_JSON | Malformed body tests |
| API-08 | quantity strict integer 1–20, not boolean; invalid 422 INVALID_QUANTITY | Type/range tests |
| API-09 | invalid SKU 422 INVALID_SKU | Unknown/type SKU cases |
| API-10 | insufficient stock 409 OUT_OF_STOCK, no partial reservation | Multi-item rollback test |
| API-11 | streamed body <=16 KiB | Exact boundary and misleading/missing length tests |
| API-12 | new order 202 queued with stable nonempty ID, durable before response | Acceptance SQL and crash test |
| API-13 | identical replay 202 same ID and queued receipt, including after completion/restart | Normalization/restart tests |
| API-14 | changed payload on accepted key 409 IDEMPOTENCY_CONFLICT | Conflict test |
| API-15 | duplicate SKU lines aggregated for stock and cost | Repeated-line and rollback tests |
| API-16 | order lookup 200 with status and exact integer total; unknown 404 ORDER_NOT_FOUND | Status/cost tests incl malformed UUID |
| API-17 | separate worker normally completes within 15s in healthy local environment | Polling integration test |
| API-18 | JSON error object with safe nonempty message and required error.code | All error paths |
| API-19 | metrics 200 text/plain Prometheus, all four required counters plus latency | Exposition and label inspection |
| DATA-01 | fixed seeds 7/12/5 once, never reset on restart | Restart test and SQL |
| RACE-01 | >=12 competing calls; never oversell or go negative | Owned distinct-key race |
| RACE-02 | eight same-key calls across two APIs: one order and decrement | Owned same-key race with instance participation |
| JOB-01 | two workers, atomic claim, unique completion effect | Competing/stale-owner tests |
| JOB-02 | kill processing worker; committed order recovers | Fault drill, SQL and logs |
| JOB-03 | bounded poison retries; persisted failed state; stock retained | Poison and final-attempt-crash tests |
| QA-01 | owned unit/integration/race tests, deliberate fail-to-pass proof | Test reports and preserved failing run |
| QA-02 | supplied checker --concurrency --stress: 15/0/0 | Fresh isolated dataset and terminal log |
| OPS-01 | multistage non-root image, Compose health/persistence and baseline size comparison | Build/inspection/restart evidence |
| CI-01 | PR-to-main lint/tests/checker/build/scan; SBOM artifact; blocking policy | Red-to-green and halted promotion |
| CI-02 | least privilege, pinned actions, immutable accepted image | Workflow review and digest |
| K8S-01 | two APIs/two workers, persistent DB, probes, resources, ConfigMap/Secret references | Cluster manifests and inspection |
| GIT-01 | Argo real repo, Synced/Healthy, manual drift restored | Git revisions and reconciliation |
| REL-01 | healthy 30s rolling probe; unhealthy rollout halted; GitOps restore | CSV/events/revisions and no order loss |
| OBS-01 | >=200 raw HTTP samples, p95, SLO targets and limitations | Raw data and calculation |
| DOC-01 | architecture/ADR/threat model/postmortem, reproducible README | Documentation review |
| SUB-01 | <=8-page report, <=15min demo, access/contribution/assistance records | Final evidence audit |

## Contract gaps to document before API implementation

The contract caps body size and key syntax but does not assign explicit codes for oversize bodies or malformed nonmissing keys. Proposed conventions: 413 REQUEST_TOO_LARGE and 400 INVALID_REQUEST respectively; these are project choices, not quoted requirements. Confirm with instructor if stricter hidden expectations exist. No need to block design work.

Validate syntax/structure before reservation; for accepted valid replays, consult the key mapping before current stock. Framework default validation responses must not replace required error codes. Unknown order text must return ORDER_NOT_FOUND rather than leaking a UUID parsing/database exception.
