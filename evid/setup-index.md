# Evidence index

Current status: Part 1 environment and document preparation verified. Runtime acceptance gates remain untested.

| ID | Requirement / check | Commit SHA | UTC run time | Commands and output | Artifacts / links | Observed result | Status |
|---|---|---|---|---|---|---|---|
| P1-ENV | Tool versions and initial environment checks | No commits yet | 2026-11-10T11:35:03Z | [Commands](01-design/20261110T113503Z_preflight/commands.txt), [output](01-design/20261110T113503Z_preflight/terminal.log) | [Results](01-design/20261110T113503Z_preflight/results.json) | Tools present; uv optional/absent; initial Docker/Git restrictions followed up separately | PASS with recorded initial failures |
| P1-DOCKER | Docker server and disposable container | No commits yet | See terminal log | Same run directory | [Follow-up results](01-design/20261110T113503Z_preflight/docker-followup.json) | Server reachable; hello-world exit 0 | PASS |
| P1-SOURCE | Unchanged supplied assessment materials | No commits yet | See run context | See context | [Source hashes](01-design/20261110T113503Z_preflight/supplied-materials.json) | Five copied files match original bytes | PASS |
| P1-DESIGN | Design files, local links and secret exclusions | No commits yet | 2026-11-10T11:39:21Z | [Output](01-design/20261110T113503Z_preflight/terminal.log) | [Review](01-design/20261110T113503Z_preflight/document-review.json), [document hashes](01-design/20261110T113503Z_preflight/design-manifest.json) | 11 documents checked; no missing local links; evidence retained and secret examples ignored; runtime proofs pending | PASS for preparation only |
| P1-MOVE | Project relocation with unchanged file contents | No commits yet | 2026-11-10T11:43:49.192416+00:00 | [Output](01-design/20261110T114349Z_relocation/terminal.log) | [Move verification](01-design/20261110T114349Z_relocation/relocation.json) | 99 files hash-verified; existing coursework preserved | PASS |
| P1-LOCATION | Current-root audit, hidden files restored, tools/source/link checks | No commits yet | 2026-11-10T11:52:08.209641+00:00 | [Commands](01-design/20261110T115205Z_rop-audit/commands.txt), [output](01-design/20261110T115205Z_rop-audit/terminal.log) | [Audit](01-design/20261110T115205Z_rop-audit/audit.json) | See audit; runtime acceptance tests not run | Preparation rechecked |
| P1-RENAME | Rename to FulfillOps and current references | No commits yet | 2026-11-10T11:54:44.582366+00:00 | [Output](01-design/20261110T115444Z_fulfillops-rename/terminal.log) | [Audit](01-design/20261110T115444Z_fulfillops-rename/audit.json) | Hashes, Git root, local links and supplied sources verified | PASS |
| P1-REMOTE | Local identity and origin setup | No commits yet | See run context | [Commands/output](01-design/20261110T115558Z_repository-setup/terminal.log) | [Results](01-design/20261110T115558Z_repository-setup/results.json) | Identity/origin verified; remote query succeeded with no HEAD or branch refs; no push | PASS |

Add one row per real run. Preserve failing and repaired runs separately. Historical records retain original execution paths; current project root is `FulfillOps`.
