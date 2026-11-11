# Part 1 environment verification

Current project root: `/Users/ferasmich/Documents/Feras/EPITA/DevOps/ROP`.

Rechecked from ROP on 10 November 2026: [current audit](../evid/01-design/20261110T115205Z_rop-audit/audit.json), [commands/output](../evid/01-design/20261110T115205Z_rop-audit/terminal.log). Historical preflight paths below describe the original run. Hidden Git/configuration entries are now inside ROP; the Git root was verified. No application tests have run.

Verified on 10 November 2026. Actual commands, stdout/stderr and exit codes: [preflight evidence](../evid/01-design/20261110T113503Z_preflight/terminal.log).

| Prerequisite | Observed result |
|---|---|
| Git | 2.45.2; local repository initialized on main; no commits |
| Python | 3.12.3 |
| pip | 24.0, available through python3 -m pip |
| Docker CLI / server | 29.8.1 / 29.8.1 |
| Docker Compose | v5.5.1 |
| Docker disposable test | hello-world completed with exit 0 |
| kubectl | v1.37.2, darwin/arm64 |
| kind | v0.33.0 |
| uv | Not installed; not required by the selected pip/venv approach |

Initial Docker socket access and Git initialization failed under execution restrictions. Retried with the necessary local access; Docker and Git initialization succeeded. Preserve both initial failures and follow-up results. The permission failure did not establish that Docker was stopped.

No application dependencies installed, database started or Kubernetes cluster created. Client versions do not prove cluster compatibility; select/test the kind node image and pin Kubernetes/Argo CD versions during the deployment stage. Image download and container execution were demonstrated only with Docker's disposable test image.

Part 2 prerequisite: resolve and lock Python packages, create/apply migrations, implement test-only seeds and start an isolated PostgreSQL environment. Solo assessment approval remains unverified.
