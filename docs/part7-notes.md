# Part 7 — Kubernetes and GitOps

## What was deployed

A local kind cluster runs PostgreSQL on persistent storage, two API replicas and two independent worker pods. Argo CD reads the real repository and reconciles the namespace-scoped configuration. API/worker containers run as non-root, use read-only filesystems and restricted database roles. CPU/memory requests and limits, startup/readiness/liveness probes and an availability-preserving API rolling strategy are defined.

The database owner password is used only by PostgreSQL/bootstrap. API and worker credentials are separate Secret references, never Git values. The AppProject limits the repository and namespace. Secrets are bootstrapped out of Git; no repository token was needed because the repository is public.

## Results on 11 November 2026

Argo was Synced/Healthy at Git revision `933b087c2aa506558de0c57ab6af93ffe1c971e1`. Both APIs and workers were ready. Logs show completed jobs from both worker pods.

The supplied checker passed 15 checks with no failures/skips on a fresh Kubernetes dataset. Separate requests went directly to both API pods:

- Eight same-key requests returned one order ID and reserved one unit.
- Twelve distinct-key requests competed for the remaining five KIT-100 units: five accepted, seven OUT_OF_STOCK.
- All 21 accepted orders completed with 21 receipts; no stock became negative.

For drift, self-healing was paused briefly to make detection observable. The API was manually scaled from two to three. Argo reported OutOfSync for that Deployment. Restoring self-healing from the committed Application made Argo restore two replicas and Synced/Healthy. There was no final manual Deployment patch.

PostgreSQL's pod was then deleted and recreated. Its pod UID changed, but PVC UID/volume stayed the same. The order, 1299-cent total, 21-order/receipt counts and stock zero were unchanged. Replaying the proof key still returned the original acceptance receipt. Automatic bootstrap reseeding did not restore spent stock.

Host regression suite: 69 passed; Ruff/formatting passed. The deployment-manifest commit also passed GitHub CI: https://github.com/Ferasmich/fulfillops/actions/runs/43075122431

## Versions and limitations

kind v0.33.0; Kubernetes v1.37.0; Argo CD v3.6.1. Node/PostgreSQL digests and the installer Git commit are pinned in source. The local application is an ARM64 rebuild from application commit `93a817a45f01d3dd3706207c8dffa706800ff0ef`. It is not the same binary image as the AMD64 CI artifact. No registry image was published.

This is one disposable node and one database, not a highly available production installation. Persistence is proven across pod replacement, not deletion of the whole kind cluster. Local Kubernetes Secrets are not a managed secret-storage/backup system. A 30-second good rollout and broken-release Git recovery are still Part 8 requirements; the rolling strategy alone does not prove them.

## Questions to prepare for

- **What does Synced mean?** The live managed objects match the desired Git manifests.
- **What does Healthy mean?** Argo's resource health checks report that the deployed components are ready; it is not a replacement for business tests.
- **Why pause repair in the drill?** To capture OutOfSync before correction. It was re-enabled from the saved Application configuration, then Argo did the repair.
- **When is self-healing safe?** For deliberate Git-owned settings such as replica count. Destructive migrations, data deletion or uncertain recovery need human review and a plan first.
- **Why are readiness and liveness separate?** A process can be alive while storage is unavailable. API liveness stays independent of the DB; worker liveness checks its heartbeat, while readiness also checks storage.
- **Why did the data survive?** The replacement PostgreSQL pod mounted the same PVC.
- **Why is the image tag older than the Argo revision?** The image tag identifies application source; the Git revision identifies deployment configuration. They can be versioned independently.
- **Where are secrets?** In local ignored configuration and the cluster, not committed manifests or evidence.
