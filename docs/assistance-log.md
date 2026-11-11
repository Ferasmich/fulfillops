# Assistance log

The course requires disclosure of external code and AI assistance. Record actual scope; do not attribute the entire project to a tool.

| Date | Assistance | Scope | Verification / limitations |
|---|---|---|---|
| 2026-11-10 | Codex assistance requested by the project owner | Reviewed supplied materials; drafted solo implementation proposal, Part 1 design/checklists and repository preparation; ran environment checks and captured outputs | No application behavior demonstrated. Design requires owner review and runtime tests. This entry does not claim the project owner's architecture, engineering decisions or verification were performed entirely by AI. |

Supplied assessment documents and scripts retain their original content; they are instructor materials, not original implementation. Technical references are linked in ADR-001. Add specific adopted external code and licenses if introduced later.

| 2026-11-10 | Codex assistance authorized for Part 2 | Implemented API, SQL migrations/runner, seed, integration tests and report notes; ran local verification | Owner performed initial environment/package/database setup. Actual automated results: 27 passing cases and Ruff. Worker, CI and GitOps remain unimplemented. |

| 2026-11-10 | Codex assistance authorized for Part 3 | Implemented separate worker, claims/leases, completion fencing, bounded retries and fault/checker tests; updated run instructions and report notes | Combined tests: 34 passed. Supplied checker: 15/0/0. Real worker subprocess killed in isolated test; no external business effects. |

| 2026-11-10 | Codex assistance authorized to continue Part 4 | Added unit tests, separated owned race tests, built temporary-copy regression demo and wrote testing/report notes | 52 tests passed; regression failed then passed as expected; supplied checker 15/0/0. No CI claim yet. |

| 2026-11-11 | Codex assistance for Part 5 | Added Dockerfiles, Compose services, restricted runtime roles, health checks, guarded test reset and isolated verification; updated report notes | Verified 58 tests, container checker 15/0/0, runtime permissions and shutdown/startup persistence; measured image sizes. Owner performed local setup and freed disk space. |

| 2026-11-11 | Codex assistance for Part 6 | Added pinned CI workflow, isolated image checks, SBOM/scanner and security-policy gate with tests; wrote policy/report notes | Local verification only: 69 tests, checker 15/0/0, SBOM/scan. Live GitHub red-to-green and registry publication are not claimed; commits/pushes await owner approval. |

| 2026-11-11 | Codex assistance for approved live CI verification | Made the owner-approved initial push, fixed Linux scanner bind-mount permissions, created the controlled regression PR and pushed its repair; collected actual CI logs/SBOM/scan/artifact records | Main quality run passed 69 tests; corrected PR passed 70. Deliberate bug stayed off main. PR unmerged and registry publication not triggered. |

| 2026-11-11 | Codex assistance for Part 7 | Added Kubernetes/Argo CD manifests, generated credentials outside Git, installed the pinned local cluster/controllers and ran pod-race, drift and storage proofs; wrote setup/report notes | Checker 15/0/0; both worker pods processed jobs; drift corrected and 21 orders/receipts survived DB pod replacement. Host tests 69 passed. Local ARM64 rebuild is distinguished from AMD64 CI artifact. Owner directs/reviews the project; no registry release or PR merge. |

| 2026-11-11 | Codex assistance authorized for Part 8 | Added safe request logs, measurement/release helpers and tests; ran worker-fault observations, real local good/bad rollouts and Git revert; wrote evidence notes/postmortem | 74 tests passed; 250/250 catalog responses, p95 54.54 ms; 120/120 good rollout and 476/476 bad-window probes; deployment gate rejected bad readiness; 21 Kubernetes orders/receipts preserved. Owner directs/reviews the project. Worker fault used a separate disposable host test database; local image is an ARM64 rebuild. No registry publication or PR merge. |

| 2026-11-11 | Codex assistance requested for final audit before presentation | Audited assignment coverage, corrected stale setup/current-status notes, verified a new source checkout/venv/private Compose stack, reproduced final tests/checker/regression/persistence and drafted the eight-page report | 74 tests; checker 15/0/0; 15 private-test orders preserved over restart. Existing 21 Kubernetes orders were not reset. Final documentation CI queue/artifact-download failure and screenshot/rehearsal handoff are reported accurately. Owner confirmed solo submission is allowed. |
