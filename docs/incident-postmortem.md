# Incident postmortem — controlled lab faults

Date: 11 November 2026. These were planned failures in my own test environments. No customer system was involved.

## API rolling-release failure

I changed only the candidate readiness path from `/health/ready` to `/health/forced-not-ready`. The application was alive, but the new path returned 404. The candidate never became ready. With maxUnavailable 0 and maxSurge 1, two healthy old pods stayed available and the rollout stopped at one new unready pod. Kubernetes reported ProgressDeadlineExceeded after the configured 90-second deadline. Argo briefly reported Progressing, then Degraded; it was still Synced because the bad configuration matched Git.

| UTC | Observation/action |
|---|---|
| 2026-11-11T20:18:33.666503+00:00 | baseline |
| 2026-11-11T20:18:35.980950+00:00 | good release push |
| 2026-11-11T20:19:08.536772+00:00 | healthy rollout passed |
| 2026-11-11T20:19:23.845402+00:00 | bad release push |
| 2026-11-11T20:21:15.149904+00:00 | unhealthy release blocked |
| 2026-11-11T20:21:17.673151+00:00 | git revert pushed |
| 2026-11-11T20:21:36.269305+00:00 | recovered |

The good change was `fa36a65f370e08672ce475e496196f315b869392`; the faulty change was `a603b17982c319f23cc8604d1a37e940811823db`; recovery was `fa72fb1dde7a3f13a681e73b3d483462d4ad9cf9`. The good probe observed 120 successful requests over 30 seconds. The fault probe observed 476 successful requests over 120 seconds, ending before final recovery verification. No sampled outage was observed; sampling cannot exclude every shorter interruption. Recovery was independently checked against the expected Git revision, two updated/ready/available replicas and Argo Synced/Healthy.

Impact: the new version could not be accepted, one extra unready pod used resources, and readiness checks produced 404s. The failed candidate was excluded from ready Service endpoints. All 21 existing orders, all 21 receipts, totals and stock matched the baseline after recovery. The test made no new order submissions during the rollout.

Mitigation: revert the faulty Git commit, push the revert, and let Argo apply it. I chose rollback because the exact previous configuration was already verified and there was no database migration to undo. Fix-forward would be reasonable for an incompatible data change requiring a planned repair; it was unnecessary for a readiness typo. A manual live patch alone would be overwritten by GitOps and would leave Git incorrect.

Root cause: the probe URL in deployment configuration did not exist in the API. Application/image CI was green for the candidate source, but that does not validate every Kubernetes probe setting. The deployment gate correctly refused acceptance. The gate does not perform automatic rollback; the drill handles the explicit revert.

Prevention: retain readiness/liveness separation, maxUnavailable 0, the release gate and the three-second preStop drain. Before a real release, add an isolated deployment smoke check that verifies the manifest's probe URLs against the running candidate (future work), and require its result before promotion. These checks reduce risk; they are not proof of production availability.

## Worker crash and recovery

This drill ran two real worker subprocesses against a separate disposable test database. Test lease/backoff values were shortened; default operational lease is ten seconds.

| UTC | State |
|---|---|
| 2026-11-11T19:07:35.885330+00:00 | Committed order queued, attempts 0, receipts 0, stock 6; live/ready 200 |
| 2026-11-11T19:07:36.071956+00:00 | First worker held the claim, attempts 1; it was then killed before completion |
| 2026-11-11T19:07:36.675073+00:00 | Second worker recovered the expired claim, attempts 2, completed, receipts 1, stock still 6 |

Root cause was the deliberate process kill after durable acceptance. The claim lease made abandoned work reclaimable. The replacement claim token fenced the old owner, and the transaction plus unique completion receipt prevented a duplicate completion effect. Retry count increased from zero to one. API health stayed 200; completion was delayed until reclamation, and the committed order/reservation survived.

Mitigation was automatic reclaim by the surviving worker. No data reset or order re-submission was needed. Bounded poison-job testing also showed three attempts, two retries and a retained failed order for manual review. This application models completion in PostgreSQL; exactly-once external payment/shipping is not demonstrated.

Prevention: keep crash/poison regression tests, monitor retry growth and terminal failed orders, and document operator reconciliation. A production external side effect would also need an idempotent downstream operation/outbox strategy.

## Evidence

[Part 8 evidence](../evid/08-reliability/README.md) contains raw CSV, health/metrics/log snapshots, gates, database comparisons and the two timelines. The failed rollout was an expected experiment result, not a hidden failed run.
