# FulfillOps - solo presentation runbook

Presenter: **Feras MICHAEL**. Solo submission is allowed. English presentation.

The assignment section 9 sets a **maximum of 15 minutes** for the demo video/live presentation. The setup checklist suggests **12-15 minutes**. This plan is **13 minutes 30 seconds**, including short evidence demonstrations and an optional code walkthrough, leaving 90 seconds of margin. These are rehearsal allocations, not a claim that a real rehearsal has been timed. The brief does not assign a separate fixed duration to questions; be ready for the individual defense.

## Timing and required coverage

| Slide | Time | Clock | What I explain/show |
|---|---:|---|---|
| 1. FulfillOps | 0:30 | 0:00-0:30 | Purpose, name, solo ownership |
| 2. A dealership and a factory | 0:50 | 0:30-1:20 | Analogy and duplicate request meaning |
| 3. The running system | 1:10 | 1:20-2:30 | Two APIs, shared database, two workers, GitOps |
| 4. One transaction reserves the stock | 1:20 | 2:30-3:50 | Atomic commit and successful replay; includes 25s evidence |
| 5. Races across both API replicas | 1:15 | 3:50-5:05 | Eight same-key requests, twelve competing requests; includes 30s evidence |
| 6. Worker crash and bounded retries | 1:10 | 5:05-6:15 | Killed worker, reclaim, unique receipt, poison state; includes 25s evidence |
| 7. Tests and CI gates | 1:10 | 6:15-7:25 | Failing test, repaired test, actual red/green PR; includes 25s evidence |
| 8. Containers and supply-chain security | 1:00 | 7:25-8:25 | Non-root, roles, secrets, SBOM, blocking/informational policy |
| 9. Git desired state and Argo CD | 1:05 | 8:25-9:30 | Synced vs Healthy, drift and self-healing |
| 10. Observed latency and metrics | 1:05 | 9:30-10:35 | 250 samples, p95 calculation, targets and limits |
| 11. Bad rollout, Git revert, recovery | 1:30 | 10:35-12:05 | Good probe, bad readiness, halted acceptance, Git recovery, incident timeline; includes 40s evidence |
| 12. What I can defend | 1:25 | 12:05-13:30 | Limits, responsibility, next work; includes optional 35s code walkthrough |

If time slips, omit the optional code walkthrough on slide 12 and keep all mandatory evidence. Do not spend the buffer waiting for CI, package installation or a new rollout. Rehearse once with a stopwatch; trim explanation instead of skipping a required proof.

## Speaker notes

### 1. FulfillOps

“My name is Feras MICHAEL. This is my solo FulfillOps project. It is an order API with shared inventory and background processing. I focused on accepting an order once, keeping accepted work durable, and recovering safely from crashes and bad updates. I will show the evidence for those claims.”

### 2. A dealership and a factory

“Imagine buying a car through a dealership. The dealership desk receives the request; this is the API. Two desks use the same reservation ledger, which is PostgreSQL. After acceptance, a factory work ticket waits for a manufacturing station, which represents a worker. If the customer retries because the first response was lost, that is still the same purchase. A genuinely new purchase needs a new request key. The analogy explains the order workflow; this program does not manufacture physical cars.”

### 3. The running system

“The Service reaches either API replica. Both use the same database, so correctness cannot depend on memory in one process. The database stores stock, orders, accepted keys, jobs, attempts and receipts. Two workers compete for durable jobs. I chose one database work table to avoid coordinating a separate broker with the order transaction. The tradeoff is polling load and a single database dependency. Git and Argo are a separate control path for deploying this software.”

### 4. One transaction reserves the stock

“For a new request, the unique key is the first database gate. The API locks product rows in SKU order, checks every line, then commits the reservation, order, key and job together. Only then does it send 202. Two dealers cannot both reserve the last car because they cannot both change the same locked stock at once. Replaying the same key and payload returns the original order ID; changing an accepted payload gives a conflict. This protects against a lost HTTP response as well as repeated clicks.”

Show the saved replay/public-checker result and API acceptance code. Point out that the replay receipt remains queued by contract even when GET order reports completed. The key and order ID are different concepts.

### 5. Races across both API replicas

“This saved Kubernetes test sent four requests to each API pod at the same moment, all with one key. All eight got one order ID and only one unit was reserved. Next, twelve new-key requests competed for five remaining units: five were accepted and seven were rejected. The database ended at zero stock. The separate fresh host test starts with seven units, so its result is seven accepted and five rejected. I keep those experiments separate.”

Show `evid/07-gitops/cross-pod-races.json`: both pod names, shared ID, and distinct-key results. Do not claim that a Service port-forward alone proves both replicas were used.

### 6. Worker crash and bounded retries

“A worker claims a job with a lease and a new token. If it dies, another worker can reclaim the expired job. The old owner cannot complete after losing its token or lease. In this real process-kill test, attempt one was interrupted, attempt two completed, and there was one receipt. Stock stayed reserved once. A poison job stopped after three configured test attempts and stayed failed for review. The normal default is five attempts. This proves the database completion effect, not exactly-once payment or shipping.”

Show crash victim/survivor logs and poison metrics. State that this worker drill used a separate disposable host database, while the rollout drill used Kubernetes.

### 7. Tests and CI gates

“The clean checkout passed 74 tests and all 15 public checker checks with no skips. I also kept a deliberate regression: Python considers True an int for isinstance, so a loose check accepts a boolean quantity. The regression test failed, then passed with the strict type check. The actual PR went red then green. CI checks source and the built image, generates an SBOM, scans it, and uploads the accepted artifact only after the gates pass. The final documentation workflow was queued at the audit; I do not call that run green.”

Show final checker summary, the saved failing/fixed regression, and PR red/green run links. Clearly label saved actual results; do not present them as a new live run.

### 8. Containers and supply-chain security

“The API and workers share one minimal image and run different commands. Runtime is non-root with a read-only filesystem and restricted database roles. Credentials stay outside Git. The scan policy blocks fixable High and Critical findings. The retained baseline scan had no blockers but 351 informational findings, including unfixed High and Critical records. Passing the policy does not mean the image has no vulnerabilities. The accepted image is a GitHub build artifact. I have not published a registry release.”

Distinguish the local ARM64 rebuild from the AMD64 CI artifact. Avoid describing an image archive checksum as a registry digest.

### 9. Git desired state and Argo CD

“Git describes the approved image and configuration. Argo compares that with Kubernetes and reconciles it. Synced means configuration matches; Healthy means resource checks pass. In the factory example, the plan asks for two operating stations: one station may work while the whole factory still does not match the plan. I demonstrated drift from two APIs to three and repair back to two. CI tests a new version of the ordering software. Argo checks the deployed software configuration. Neither checks the options of a physical car.”

Show saved OutOfSync and corrected Synced/Healthy proof, or the current read-only cluster status. Explain when self-healing is suitable and why uncertain/destructive data changes need a separate plan.

### 10. Observed latency and metrics

“I measured 250 sequential catalog requests. All succeeded and p95 was 54.54 milliseconds. Nearest-rank p95 is the 238th duration after sorting the 250 observations. My proposed local targets are at least 99.5 percent success and p95 below 300 milliseconds. The measured window met them, but this short test does not prove monthly availability or performance under real production traffic. Database business counters are the same on both APIs, so adding them would double count; HTTP counters belong to each process.”

Show raw CSV and JSON summary; mention tunnel/proxy overhead and that this measured GET catalog, not POST order creation.

### 11. Bad rollout, Git revert, recovery

“The good 30-second probe saw 120 successful responses during actual pod replacement. Next I changed readiness to a URL that returned 404. The candidate process was alive but never ready, so it never entered ready Service endpoints. Both old healthy APIs kept serving. At the 90-second deadline Kubernetes reported failed progression and Argo became Degraded. The deployment gate rejected acceptance; image CI did not detect this manifest typo. I reverted the bad Git commit and pushed it, then Argo restored the expected configuration. All 21 committed orders and 21 receipts were unchanged.”

Show timeline, bad gate/Argo snapshot and recovery gate/order comparison. The 120-second fault probe had 476 successes; it covers the fault and start of revert, ending before final recovery verification. Do not claim it observed the complete recovery window. Kubernetes did not automatically revert Git. Explain rollback instead of fix-forward: the previous configuration was already good and there was no data migration to undo.

### 12. What I can defend

“The main design choice was keeping acceptance and work in one PostgreSQL transaction. The main limitations are the single-node/database lab, missing production authentication and backup recovery, and no external shipping/payment effect. I would add order authorization, a backup/restore drill and manifest probe smoke tests. I am responsible for explaining this whole solo project. The actual scope of implementation and verification assistance is disclosed in the course-required log. I can walk through the acceptance transaction or worker ownership check.”

Optional code walkthrough: `api/main.py` function `accept`; `worker/main.py` functions `owns` and `complete`. If time is short, offer to open these during questions instead.

## Prepare the demonstration workspace

Open Canva, the repository in VS Code, PR #1 and the saved evidence files before starting. Use one terminal, large readable text and a stopwatch. Do not display .env, database passwords, Argo credentials or kubeconfig. Do not install tools or run the long failure drill during the timed talk.

Required evidence tabs, in speaking order:

1. `evid/09-final/public-checker.txt`: replay and full final 15/0/0 result.
2. `evid/07-gitops/cross-pod-races.json`: identical-key and competing-key calls.
3. `evid/08-reliability/worker-fault/worker-crash-timeline.json`, crash victim/survivor logs and poison logs/metrics.
4. `evid/09-final/regression-failing.txt` and `regression-fixed.txt`; real PR runs in `docs/ci-live-results.md`.
5. `evid/07-gitops/application-drift.json` and `application-after.json`.
6. `evid/08-reliability/http-samples.json` and raw CSV.
7. `evid/08-reliability/release-summary.json`, bad/recovery gates and before/after orders.

A quick read-only live cluster view is safe:

```bash
kubectl --context kind-fulfillops -n fulfillops get pods
kubectl --context kind-fulfillops -n argocd get application fulfillops
```

The retained Kubernetes stock is spent. Do not run a fresh-data checker against it or reset it for the presentation. If asked to reproduce worker tests, use their separate disposable database with a new evidence directory:

```bash
FULFILLOPS_EVIDENCE_DIR=/tmp/fulfillops-defense-proof python -m pytest tests/integration/test_worker.py -v -s
```

If asked to reproduce the full rollout, explain that `scripts.release_drill` pushes real lab commits and takes longer than the short evidence segment. Follow `docs/reliability.md`, preserve earlier evidence, and use only the owned lab.

## Likely defense questions

- Why does the idempotency mapping come before stock reservation, and how does the deferred foreign key work?
- What happens if the transaction commits but the HTTP response is lost?
- Why does a Python lock fail across API replicas?
- What prevents a delayed worker with an old lease from completing?
- Why is failed stock retained, and what would operator reconciliation need?
- Why can Synced still be Degraded? Who actually reverted Git?
- What did the scan policy accept, and what vulnerabilities remain visible?
- Why is 54.54 ms not a production performance guarantee?
- How would authentication, backups and external side effects change this design?

Source: supplied assignment sections 5, 8 and 9; setup guide checklist section 8; verified project evidence. Keep actual live/replayed results distinct.
