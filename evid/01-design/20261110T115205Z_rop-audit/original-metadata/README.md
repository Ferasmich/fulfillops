# FulfillOps

Solo implementation of the resilient order-processing capstone. This repository currently contains preparation and design only. No API, worker or runnable stack is implemented yet.

- [Implementation proposal](Project%20Implementation.md)
- [Architecture](docs/architecture.md)
- [Architecture decision](docs/ADR-001.md)
- [Database design](docs/database-design.md)
- [Acceptance checklist](docs/acceptance-checklist.md)
- [Threat model](docs/threat-model.md)
- [Environment checks](docs/environment.md)
- [Evidence index](evid/INDEX.md)

The official assignment specifies teams of 2–3; instructor agreement for solo submission remains unverified. The technical requirements are unchanged.

## Layout

`api/`, `worker/` and `common/` will contain application code; `db/migrations/` schema changes; `tests/` owned tests; `assessment/` unchanged supplied materials; `infra/` deployment definitions; and `scripts/` operational helpers. Empty directories are preparation only.

All verification artifacts, including terminal commands/output, live under `evid/`. Maintained design documents stay under `docs/`. README and reports will link to evidence rather than duplicate it. No runtime installation, startup or teardown instructions are claimed until implemented and verified.

## Dependency management

Target Python 3.12 and PostgreSQL 16. Use a project-local virtual environment and pip, with runtime and development inputs under `requirements/`. During Part 2, resolve exact versions into committed, reproducible lock files and verify installation before introducing runtime code. No dependencies are installed or locked yet. Do not install into the system Python.

No commits, remote publication or submission have been made as part of preparation.
