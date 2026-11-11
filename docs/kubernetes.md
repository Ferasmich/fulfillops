# Kubernetes and Argo CD setup

This is the local kind lab, separate from Docker Compose. Use the explicit context `kind-fulfillops` for every command. Do not run these commands against another cluster.

Versions used: kind v0.33.0, Kubernetes v1.37.0 (node digest in `infra/kind/cluster.yaml`), Argo CD v3.6.1 (installer commit/URL in `infra/argocd/version.json`). This Mac and its kind node are ARM64.

## New cluster

From a clean project checkout, with Docker running and development dependencies installed:

```bash
kind create cluster --name fulfillops --config infra/kind/cluster.yaml --wait 120s
git archive 93a817a45f01d3dd3706207c8dffa706800ff0ef | docker build --tag fulfillops:93a817a45f01d3dd3706207c8dffa706800ff0ef -
kind load docker-image fulfillops:93a817a45f01d3dd3706207c8dffa706800ff0ef --name fulfillops
python -m scripts.k8s_secrets
kubectl --context kind-fulfillops create namespace argocd
kubectl --context kind-fulfillops apply -n argocd --server-side --force-conflicts -f https://raw.githubusercontent.com/argoproj/argo-cd/94037c4d4e1af4bd0651d37a179fbd9e347e668c/manifests/install.yaml
kubectl --context kind-fulfillops -n argocd wait --for=condition=Available deployment --all --timeout=240s
kubectl --context kind-fulfillops -n argocd rollout status statefulset/argocd-application-controller --timeout=240s
kubectl --context kind-fulfillops apply -f infra/argocd/project.yaml -f infra/argocd/application.yaml
kubectl --context kind-fulfillops -n argocd wait --for=jsonpath='{.status.sync.status}'=Synced application/fulfillops --timeout=240s
kubectl --context kind-fulfillops -n argocd wait --for=jsonpath='{.status.health.status}'=Healthy application/fulfillops --timeout=240s
```

Do not create a second cluster with the same name if it already exists. The image is built from the exact CI-validated application commit; the deployment configuration has a newer Git revision. `imagePullPolicy: Never` is intentional for this local image-loading setup. Load the image on all kind nodes before syncing. A registry-based environment would need a published image/digest and an appropriate pull policy.

The secret helper creates the application namespace and credentials outside Git. It adds `K8S_*_PASSWORD` values to ignored `.env` when needed, then sends the Secret directly to Kubernetes without printing values. Existing Secrets are left unchanged. Preserve the original credentials with the database; the helper refuses to generate new ones when a PVC already exists and the local values are missing.

## What Argo manages

The real public repository is `https://github.com/Ferasmich/fulfillops.git`, branch main, path `infra/k8s`. No GitHub token is needed for this public source.

Argo applies ConfigMap/services first, then the PostgreSQL StatefulSet and PVC, then the bootstrap job, then two API/two worker replicas. The PVC and database are in the same sync wave so storage waiting for its first consumer cannot block database creation. The bootstrap hook applies migrations, seeds only missing test products and provisions runtime roles. A completed bootstrap pod is normal.

The AppProject restricts the source repository, target namespace and resource kinds. Secrets are not Git-managed. Automatic self-healing is enabled; automatic pruning is disabled, with an extra PVC prune guard. Database backup and high availability are not provided by this one-node lab.

## Access

In a VS Code terminal:

```bash
kubectl --context kind-fulfillops -n fulfillops port-forward --address 127.0.0.1 svc/fulfillops-api 8081:80
```

Open `http://127.0.0.1:8081/health/ready` or `/api/v1/catalog`. Compose uses port 8080 and a different database. Kubernetes test stock is zero after the recorded full checker/races; that is expected.

For Argo's optional UI, use a separate terminal:

```bash
kubectl --context kind-fulfillops -n argocd port-forward --address 127.0.0.1 svc/argocd-server 8443:443
```

Open `https://127.0.0.1:8443` (local self-signed certificate), username `admin`. On this Mac, copy the initial password to the clipboard without printing it:

```bash
kubectl --context kind-fulfillops -n argocd get secret argocd-initial-admin-secret -o jsonpath='{.data.password}' | base64 --decode | pbcopy
```

Do not paste the password into chat or save it in evidence.

## Reproduce the proof

On a newly seeded isolated lab dataset:

```bash
python -m scripts.verify_gitops
```

This runs the public checker, same-key and competing-key requests split across the two actual API pods, drift detection/correction and PostgreSQL pod replacement. It saves required outputs in `evid/07-gitops/`. It deliberately consumes test stock, temporarily scales the API to three replicas and deletes only the owned database pod; it retains the PVC. Self-healing is paused briefly to capture OutOfSync, then restored from the committed Application file before automatic repair.

On the already-used dataset:

```bash
python -m scripts.verify_gitops --repeat
```

Repeat mode skips the checker/races and reuses the saved proof order for drift/storage checks. It does not reset data. The original checker/race files stay available.

A Service port-forward selects a pod; it is not proof of traffic balancing during a rollout. The race script forwards to each API pod explicitly. The continuous rollout measurement is separate Part 8 work.

## Stop and cleanup

Ctrl+C stops a port-forward, not the app. The cluster keeps running. `kind delete cluster --name fulfillops` removes this entire disposable cluster and its database storage. Do not use that as an ordinary stop/recovery command or before preserving the evidence you need.
