# Part 7 evidence

Verified on 11 November 2026 in the owned `kind-fulfillops` cluster.

- [Verification transcript](verification.txt): actual commands/results, Git revision, replicas, races, drift repair, persistence and rollout history.
- [Public checker](public-checker.txt): **15 passed / 0 failed / 0 skipped** on a fresh isolated Kubernetes dataset.
- [Cross-pod race responses](cross-pod-races.json): eight shared-key calls across both pods; competing-key results and pod names.
- [Before](application-before.json), [drift](application-drift.json), [after](application-after.json): Synced/Healthy → API OutOfSync at three replicas → Synced/Healthy at two.
- [Before database state](database-before.json), [after](database-after.json), [storage proof](storage-proof.json): 21 completed orders/receipts and stock unchanged; new database pod, same PVC/volume.
- [Both worker logs](worker-logs.txt): completion records from both independently running workers.
- [EndpointSlice](service-endpoints.json): Service endpoints for both API pods.
- [Image/platform](image-platform.json): local ARM64 image and cluster architecture; not confused with AMD64 CI image.
- [Cluster setup](cluster-setup.txt), [Argo install](argocd-install.txt), [server validation](manifest-validation.txt), [Argo validation](argocd-validation.txt), [local image build/load](local-image-build.txt).
- [Host regression tests](local-tests.txt), [JUnit](local-tests.xml): **69 passed**, with one upstream TestClient deprecation warning; Ruff/formatting passed.

Repeat instructions: [Kubernetes guide](../../docs/kubernetes.md). `python -m scripts.verify_gitops` requires a fresh dataset; `--repeat` skips destructive checker/race consumption and reuses the proof order. It never resets the database. The default proof script temporarily pauses repair only to observe drift, then restores the Application and lets Argo reconcile.

No credentials, Secret data, Argo admin password or kubeconfig are saved here. Part 8's continuous rollout probe and unhealthy-release recovery remain pending.
