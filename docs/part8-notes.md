# Part 8 — report and defense notes

## What I did

I added safe JSON request logs and kept the four required counters plus the latency histogram. I measured 250 catalog requests through the Kubernetes Service: 250 succeeded and p95 was 54.54 ms. This met my proposed local-window targets of 99.5% success and p95 below 300 ms.

I started the supplied 30-second probe before updating the two API replicas. All 120 requests succeeded. Then I used a bad readiness URL. The new pod stayed unready, the old pods kept serving, and the release gate rejected the rollout. I reverted the bad Git commit; Argo returned to Synced/Healthy. The same 21 orders and 21 receipts were present afterwards.

For the other fault, I killed a worker holding a committed job in a disposable database. The second worker recovered it after lease expiry and wrote one completion receipt. Retries increased by one and stock was reserved only once. The worker drill used host processes; the rolling release used Kubernetes.

## Questions I should be able to answer

- **What is p95?** After sorting 250 durations, the 238th value is the nearest-rank p95. About 95% of these observations were at or below it; it is not the average or a promise for every request.
- **Did I prove 99.5% monthly availability?** No. I proposed a target and measured a short local window. There was no realistic production load or internet path.
- **Why was the bad application alive but unready?** The process worked; its configured readiness URL returned 404. Readiness controls traffic, while liveness controls restart decisions.
- **Why did users still get responses?** maxUnavailable 0 kept both healthy old pods. Service endpoints excluded the bad pod. The probe forwarded to the real Service without retries.
- **Can Synced be unhealthy?** Yes. Git can contain a bad configuration. Synced means it was applied; Healthy means the resources passed health checks.
- **Who rolled back?** The drill created and pushed a Git revert. Argo reconciled that revision. Kubernetes did not automatically edit or revert Git.
- **Did CI catch this typo?** No claim of that. Image CI passed; the deployment gate detected the failed readiness/progression. A manifest probe smoke test is a follow-up improvement.
- **Why are business counters not added across pods?** Each API reports the same database totals. Adding them counts the same orders twice; use max. HTTP counters are per-process and can be summed.
- **Why did the worker not complete twice?** A lease/claim token controls ownership and a unique receipt plus transaction protects the final effect. An external shipping/payment service would need its own idempotency design.
- **What should I show?** The raw 250-sample CSV/summary, good/bad/recovery gate results, Argo Degraded then Healthy snapshots, unchanged order snapshots and worker recovery log. No new screenshot is needed for the saved evidence.

[Evidence](../evid/08-reliability/README.md), [reproduction/metrics](reliability.md), [postmortem](incident-postmortem.md).
