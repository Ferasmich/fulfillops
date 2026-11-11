# Final project audit

Audit date: 11 November 2026. Solo submission is allowed, as confirmed by the project owner. This checks the implementation and saved proof against the supplied assignment; it is not a prediction of the grade.

| Requirement | Verified proof | Result |
|---|---|---|
| Architecture, ADR, threat model | docs/architecture.md, ADR-001.md, threat-model.md | Complete; PostgreSQL work table and transaction boundaries explained |
| Exact API, migration/seed/reset behavior | tests/integration/test_api.py, unit cases, final fresh checker | Complete; 74 full tests and checker 15/0/0 |
| Atomic cross-replica idempotency | evid/07-gitops/cross-pod-races.json; final owned races | Eight shared-key calls across two pods, one ID/reservation; 12 competing-key calls with correct stock |
| Worker resilience and poison handling | evid/08-reliability/worker-fault/; final worker tests/logs | Real process kill, second-worker reclaim, one receipt; bounded retries and retained failed stock |
| Docker, hardening and persistence | evid/05-containers/ and 09-final/ | Non-root/read-only/restricted roles; clean build/stack; full down/up preserves 15 final-test orders |
| PR red-to-green, scan policy and CI SBOM | evid/06-ci/github/; run 43084811974; 09-final/application-ci-artifacts.json | Required live red-to-green and CI artifacts exist; baseline scan 0 blockers, 351 informationals |
| Immutable accepted image artifact | Candidate SHA-tagged accepted-image artifact in GitHub | Complete for GitHub build-artifact publication; no container-registry publication claimed |
| Kubernetes/Argo, two APIs/two workers, drift and PVC | evid/07-gitops/; infra/; Part 8 recovery | Verified real repo sync, drift repair and retained 21 orders/receipts |
| Safe rolling delivery and Git recovery | evid/08-reliability/ | Good 30s probe 120/120; unhealthy release rejected; Git revert restores health, 21 orders preserved |
| Metrics, latency/SLO, two failures and postmortem | docs/reliability.md, incident-postmortem.md; evid/08-reliability/ | 250/250 catalog samples, p95 54.54 ms; both faults documented with health/metrics/logs |
| Fresh install and final checker | evid/09-final/clean-checkout.txt, tests.txt, public-checker.txt | Passed from clean tracked source and a new Python environment/private stack |
| Required report | evid/09-final/FulfillOps-report.pdf | Eight pages; rendered and inspected |
| Contribution/assistance and public instructor access | README, docs/assistance-log.md; GitHub visibility public | Solo responsibility stated; accurate scoped disclosure; no private invite needed |
| Final presentation/demo | To be prepared in Canva with timed solo runbook | Remaining delivery artifact; maximum 15 minutes |

## What still needs an actual outcome

- GitHub's workflow for the final evidence commit was queued with no jobs at the audit snapshot. The application candidate passed CI; the queued documentation run is not claimed green. Newer artifact downloads returned HTTP 502. Preserve the existing CI proof and recheck the remote outcome before final submission.
- The brief requests a grading screenshot showing the complete public checker with no skips. The authentic final terminal output is saved; capture it in VS Code. Automatic Terminal computer capture was unavailable. Do not manufacture a screenshot.
- Rehearse the solo presentation and submit the repository/report/presentation through the instructor's chosen channel. No upload/email to the instructor has been performed.

## Deliberate lab limits, not hidden completion claims

The Kubernetes node is ARM64 and runs a local rebuild from candidate d9a144c; the CI artifact is AMD64. Local image loading is allowed by the setup guide. Registry promotion and PR #1 merge remain unperformed. No GHCR digest, production HA, backup-restore proof, external exactly-once side effects or production authorization is claimed. The scan policy permits visible unfixed High/Critical findings; production use needs further review.

The final fresh Compose verification recreated its own stack, not the existing kind cluster. Kind installation/drift/storage proof was collected in Part 7; Part 8 actually exercised the current rolling configuration. The stale image tag in the new-cluster guide was corrected during this audit. Earlier stage notes and evidence remain historical snapshots.
