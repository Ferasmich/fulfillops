# Reliability checks

## What I measure

`/health/live` checks that the API process responds. `/health/ready` also checks storage and migrations. Kubernetes sends Service traffic only to ready pods. A failed readiness check does not mean the process should be restarted; liveness is separate.

`/metrics` exposes Prometheus text:

| Metric | Meaning | Across replicas |
|---|---|---|
| `fulfillops_http_requests_total` | Requests by method, route template and status | Sum per-pod counters/rates |
| `fulfillops_http_request_duration_seconds` | Server request-duration histogram | Combine buckets before calculating p95 |
| `fulfillops_orders_created_total` | Accepted orders stored in PostgreSQL | Same global count on each API; use max, not sum |
| `fulfillops_orders_failed_total` | Orders whose retries are exhausted | Same global count; use max |
| `fulfillops_worker_retries_total` | Sum of job attempts after the first attempt | Same global count; use max |

Business counts survive API restarts because they are queried from the database. They are cumulative within a retained dataset; deliberately deleting/resetting test data resets them. HTTP counters/histograms belong to each process and reset when it restarts. Failed orders are different from rejected HTTP requests: an OUT_OF_STOCK response is visible in HTTP status metrics, but never becomes an accepted failed order.

The API emits timestamped JSON request logs with method, route template, status and duration. It omits request bodies, customer values, query strings, headers and idempotency keys. Worker JSON logs include order IDs and claim/retry/completion events for diagnosis. Infrastructure startup messages may still be plain text. There is no central log or Prometheus server in this local lab; saved exposition and logs are the evidence.

If a Prometheus server is added, a five-minute catalog p95 expression is:

```promql
histogram_quantile(0.95, sum by (le) (rate(fulfillops_http_request_duration_seconds_bucket{route="/api/v1/catalog"}[5m])))
```

## Targets and measurement

Proposed targets: at least 99.5% successful requests and p95 below 300 ms over the declared evaluation window. A failure is a non-2xx response or transport failure (recorded as status 0). The saved latency experiment uses 250 sequential GET catalog requests; nearest-rank p95 is sorted duration number `ceil(0.95 * 250) = 238` (one-based).

```bash
python -m scripts.http_samples --base-url http://127.0.0.1:8081 --samples 250 --output /tmp/catalog-samples.csv
```

This records raw values and a JSON calculation. It uses no retries. A short loop on one machine cannot prove monthly availability, behavior under production load, POST-order latency, multi-node resilience or internet latency. Report the endpoint, sample count and window with the result. The Part 8 saved run includes a local tunnel and a stable measurement proxy; server histogram values omit that extra client/network overhead.

## Repeating the fault drills

Worker crash and bounded poison job, in a disposable database:

```bash
FULFILLOPS_EVIDENCE_DIR=/tmp/fulfillops-worker-proof python -m pytest tests/integration/test_worker.py -v -s
```

The crash test starts two real worker subprocesses, kills the worker holding a committed job and waits for the second worker to recover it. Lease timings are shortened for the test. The test records health, metrics and database state before/during/after. It does not reset the Kubernetes database.

The rolling-release exercise uses the unchanged instructor probe. A direct Service port-forward attaches to one pod and can disconnect when that pod is replaced. For the saved test, a temporary stable proxy pod forwards each GET once to the real API Service, without retries. It is test plumbing outside Argo's managed manifests, and is removed afterwards.

To prepare another owned local drill, create the ConfigMap from `infra/lab/probe_proxy.py`, apply `infra/lab/probe-pod.yaml`, and load a CI-passed ARM64 image into kind. Then use:

```bash
python -m scripts.release_drill --candidate FULL_CI_PASSED_SOURCE_SHA --confirm-lab-git-push
```

This command commits and pushes to main, changes the local cluster through Argo and overwrites its Part 8 output filenames. Preserve an earlier evidence folder before intentionally repeating it. Use it only for this owned lab, with a preloaded candidate and the existing committed orders. It runs the supplied 30-second good-release probe, a separate 120-second bad-release/recovery probe and 250 catalog measurements. It changes the bad readiness path back using `git revert`, never by resetting the database.

The release gate requires the expected Git revision/template, two updated/ready/available replicas and Argo Synced/Healthy. `Synced` alone can describe an unhealthy desired configuration. A bad candidate stays out of Service endpoints; maxUnavailable 0 retains healthy old pods. Kubernetes reports ProgressDeadlineExceeded; the gate rejects acceptance. The gate itself does not automatically roll back: the drill performs and pushes the explicit Git revert. Application/image CI and deployment health are separate checks; a wrong readiness URL can pass image CI.

After a repeat, remove only the temporary probe pod and ConfigMap. Keep PostgreSQL/PVC and application resources. See [results and evidence](../evid/08-reliability/README.md) and [postmortem](incident-postmortem.md).
