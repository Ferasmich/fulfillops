# Threat model

Design review only. Trust boundaries: HTTP client → API; API/worker → database; CI → registry; Git/Argo CD → cluster; operator → test-reset tooling. Assets: stock, durable orders, credentials, artifacts and evidence.

| Threat | Mitigation to implement | Planned verification |
|---|---|---|
| SQL injection in SKU/key/customer fields | Parameterized SQL, no string interpolation | Hostile strings treated as data |
| Overselling through concurrent requests | Atomic reservation, ordered row locks, stock constraint | Different-key race and SQL counts |
| Duplicate reservations from replay across replicas | Unique durable key, canonical comparison, acceptance transaction | Eight same-key calls across both APIs |
| Duplicate completion after lease expiry | Claim-token fencing and one transactional receipt | Stale worker resumes after reclaim |
| Oversized/malformed request exhausts resources | Streaming body cap, strict types, bounded DB waits | No/false Content-Length, invalid JSON, booleans |
| Secret leakage in Git/logs/evidence | Ignore local env, secret references, safe error categories, inspect saved outputs | Tracked-file/log review and CI secret scan |
| Credential compromise permits destructive DDL | Separate migration/API/worker roles and scoped permissions | Negative grant tests |
| Reset destroys a live dataset | Test-only tooling, environment/name/host guard, no reset HTTP route | Reject non-test and ambiguous targets |
| Dependency/image tampering | Locked dependencies, reviewed pins, SBOM/scans, digest promotion | CI artifacts and blocked critical finding |
| Broken revision reaches healthy environment | Readiness, availability-preserving rollout, explicit promotion gate and Git revert | Failed rollout and GitOps restoration |
| Metrics/logs disclose customer data or exhaust cardinality | Route-template labels, no keys/customer identifiers, bounded errors | Inspect metrics/log samples |
| Unauthorized access to order lookup | Isolated lab access; unpredictable IDs do not replace authorization | Verify local exposure; document production authentication/ownership as future work |

The public contract has no authentication scheme. Keep the exercise isolated and document that production deployment would require authentication, per-order authorization, restricted metrics, TLS and operational access control. No security testing against other systems.
