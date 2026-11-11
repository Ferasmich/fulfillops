# Evidence checklist

This lists the evidence needed for the assignment. Add a file or link when it is ready. Parts 2–8 and final clean-checkout checks are ready. See the final audit for presentation/submission actions.

| Part | Evidence | Status / location |
|---|---|---|
| Design | Architecture diagram, ADR and threat model (at least five threats) | Drafts in [architecture](../docs/architecture.md), [ADR](../docs/ADR-001.md) and [threat model](../docs/threat-model.md) |
| Database | Schema and migrations | [Design](../docs/database-design.md), migrations 001–003; [results](02-api/README.md) |
| API | Replay, correct stock and totals, persistence after restart | [27 passing cases and results](02-api/README.md) |
| Concurrency | 12+ competing requests; eight same-key requests across two APIs; duplicate-line handling; order/stock queries | [52 tests, dedicated races and failing/fixed regression](04-tests/README.md); [checker 15/0/0](04-tests/worker/public-checker.txt) |
| Worker | Two workers; crash recovery exactly once; bounded poison retries; failed state with stock retained | [Crash/poison tests and logs](03-worker/README.md) |
| Tests | Unit/integration/owned race results; failing test then corrected run; checker 15 passed, no failures/skips | [52 tests, dedicated races and failing/fixed regression](04-tests/README.md); [checker 15/0/0](04-tests/worker/public-checker.txt) |
| Containers | Clean build, healthy Compose, non-root user, persistence, image-size comparison | [Build, health, persistence and size comparison](05-containers/README.md) |
| CI | PR/run URLs, red-to-green, blocked promotion, SBOM, scans, immutable image reference | [Live PR red-to-green, CI SBOM/scan and accepted image](06-ci/README.md); registry promotion not triggered |
| GitOps | Two API/two worker pods, Argo Synced/Healthy, manual drift correction, rollout history | [Live sync, replicas, drift correction and storage proof](07-gitops/README.md) |
| Reliability | Two fault drills, healthy 30-second rollout CSV, unhealthy rollout stopped and restored through Git | [Actual fault, rollout and latency results](08-reliability/README.md) |
| Observability | Required metrics, 200+ HTTP samples, p95 calculation, SLO targets and limitations | [Actual fault, rollout and latency results](08-reliability/README.md) |
| Incident | Timeline, cause, recovery and prevention | [Postmortem and evidence links](../docs/incident-postmortem.md) |
| Submission | Repository access, <=8-page report, <=15-minute demo, contribution note, assistance log, install/teardown commands | [Final checks, eight-page report and audit](09-final/README.md); presentation/rehearsal and final CI queue outcome remain |

[Earlier setup records](setup-index.md) are kept for reference, not as required submission evidence.
