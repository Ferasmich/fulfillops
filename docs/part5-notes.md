# Part 5 — Docker and Compose

## What changed

API and workers share one image with different commands. The first build stage downloads wheels for pinned runtime packages. The runtime stage installs them and copies only application code and migrations. Development tools, pip cache, local secrets and Git/evidence folders are excluded. Python and PostgreSQL bases are pinned by digest.

The application runs as UID/GID 10001, with read-only root filesystems, writable temporary storage, dropped capabilities and no privilege escalation. API readiness and worker heartbeat/storage checks control health. The database uses a named volume.

Compose waits for database health and successful init before starting the API and two workers. Init handles migrations, non-destructive test seeding and runtime grants. The API cannot create tables, and the worker cannot modify inventory. Only init uses the database owner credentials.

## Results — 11 November 2026

The isolated stack passed the full checker: 15 passed, no failed/skipped checks. Runtime inspection confirmed non-root user and read-only filesystems. The image had no pytest, local `.env` or Git metadata. Negative privilege tests passed.

An order completed with total 1299 cents and KIT-100 stock five. It survived API/worker restart and a full `down`/`up` with the volume retained. Its replay kept the original ID and stock. A production-labelled reset was refused. Confirmed reset succeeded only on the private test dataset after the persistence proof. Cleanup removed only that uniquely named verification project and volume.

| Image | Local uncompressed bytes |
|---|---:|
| Optimized | 192,614,009 |
| Naive baseline | 264,756,846 |
| Saved | 72,142,837 (about 27.2%) |

The baseline uses the same pinned slim base/source but installs dev packages in one stage, retains pip cache and uses root. The difference measures those combined changes, not multi-stage builds alone. It is not a registry download-size comparison.

Full regression suite: 58 passed. Ruff/formatting passed. One upstream TestClient/HTTPX deprecation warning remains.

## Environment limitation

Docker failed to start during the first attempt; its log recorded no space left on device. Verification succeeded after disk space was freed and Docker restarted. The default working volume was absent and Docker created a fresh one. Earlier manual orders are not claimed to exist there. The new persistence proof is from the isolated verification run; its script never removes the working volume.

## Professor questions

- **Image versus container?** A package versus a running instance of that package.
- **Why one image?** API and worker share code/packages but run different commands.
- **Why multi-stage?** Build/download work stays outside the runtime; wheel files are mounted during install rather than retained in another image layer.
- **Why non-root?** To limit what a compromised process can change; it is one security control, not a guarantee.
- **Why a volume?** Replacing containers must not erase the database.
- **Why startup conditions?** Running is not the same as ready; storage and migrations must be ready first.
- **Why separate database roles?** Each process gets the operations it needs; workers do not reserve stock and runtime processes do not migrate schemas.
- **Does shutdown erase orders?** `docker compose down` keeps the volume; explicit volume removal destroys its data.

Next: Part 6 CI, scanning, SBOM and enforced quality/promotion gates. Nothing committed, pushed or published.

References: [Docker multi-stage builds](https://docs.docker.com/build/building/multi-stage/), [Compose startup order](https://docs.docker.com/compose/how-tos/startup-order/).
