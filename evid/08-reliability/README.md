# Part 8 evidence

## Results — 11 November 2026

- Local suite: **74 passed**, one upstream TestClient warning. [Output](tests.txt), [JUnit](tests.xml). Application candidate [CI passed](https://github.com/Ferasmich/fulfillops/actions/runs/43084811974).
- Good rolling update: **120 / 120 successful**, zero failures in the supplied 30-second probe. [CSV](good-rollout.csv), [probe output](good-probe.log), [healthy gate](good-gate.json). New API pods were created at 20:18:54 and 20:18:59 UTC, within the probe window; Deployment progression completed at 20:19:04.
- Catalog latency: **250 / 250 successful**, observed p95 **54.54 ms**. [Raw CSV](http-samples.csv), [calculation/targets](http-samples.json). Nearest rank uses the 238th sorted duration.
- Deliberately wrong readiness URL: gate rejected it with **ProgressDeadlineExceeded**. [Gate](bad-gate.json), [Argo Degraded](bad-application.json), [pod state](bad-pods.json), [Service endpoints](bad-endpoints.json), [events](bad-events.txt). The new pod was not a ready endpoint; both old healthy pods remained available.
- Bad-release probe: **476 / 476 successful**, zero failures over 120 seconds. [CSV](bad-rollout.csv), [output](bad-probe.log). This window includes the fault and the start of Git recovery; it ends before the final recovery gate. Final readiness/health is verified separately by [recovery gate](recovery-gate.json) and [recovery state](recovery-application.json).
- Git revert restored Synced/Healthy. [Before data](orders-before.json) equals [after data](orders-after.json): **21 orders and 21 receipts**, totals and stock unchanged.
- Separate worker crash: [timeline](worker-fault/worker-crash-timeline.json), [killed worker](worker-fault/crash-victim.log), [recovering worker](worker-fault/crash-survivor.log). Metrics: [before](worker-fault/crash-before.prom), [during](worker-fault/crash-during.prom), [after](worker-fault/crash-after.prom). Attempts 0 → 1 → 2, retries 0 → 1, one final receipt, stock 6 throughout. Health stayed 200.
- Bounded poison job: both [worker A](worker-fault/poison-a.log) and [worker B](worker-fault/poison-b.log), [final metrics](worker-fault/poison-after.prom): one failed order, two retries after three attempts. The test asserts retained reservation and final failed state.

## Scope and reproduction

API release drill: local kind v0.33.0, Kubernetes v1.37.0, Argo CD v3.6.1, one ARM64 node, PostgreSQL PVC, two APIs and two workers. Image `fulfillops:d9a144cca067221ef8f02e3d652548cc85dcf0e4` is the local ARM64 rebuild of CI-passed source, not the identical AMD64 CI binary. No registry publication.

Worker fault: two host subprocesses and a separate disposable PostgreSQL test database, with shortened lease/backoff timings. It is not presented as a Kubernetes worker kill. It did not modify the retained Kubernetes orders.

[Reproduction guide](../../docs/reliability.md), [drill source](../../scripts/release_drill.py), [instructor probe](../../assessment/fulfillops_rollout_probe.py), [actual commands/output](release-drill.txt), [UTC timeline and revisions](release-summary.json). The instructor probe is unchanged. The stable temporary proxy forwards once to the real API Service without retries; it avoids a port-forward pinned to a replaced API pod. Temporary proxy resources are removed after measurement.

The saved catalog window is 2026-11-11T20:19:08.692568+00:00 to 2026-11-11T20:19:21.497056+00:00. One local sequential read-only test does not establish a production SLO, POST-order performance, distributed load or monthly availability. Proposed window targets are 99.5% success and p95 below 300 ms; observed values met those targets in this window.

The deployment acceptance gate rejected the bad configuration; this is not a claim that image CI detected the readiness typo. Kubernetes retains the old pods but does not itself revert Git. The drill explicitly commits and pushes the revert for Argo to reconcile.

[Postmortem](../../docs/incident-postmortem.md), [report/defense notes](../../docs/part8-notes.md).
