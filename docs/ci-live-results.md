# Live GitHub CI results

Verified on 11 November 2026. Repository: https://github.com/Ferasmich/fulfillops

| Run | Result | What it proves |
|---|---|---|
| [Initial main](https://github.com/Ferasmich/fulfillops/actions/runs/43070297512) | Failed at SBOM generation | Trivy could not read its bind-mounted archive on Linux. Tests/build had passed. Promotion skipped. |
| [Corrected main](https://github.com/Ferasmich/fulfillops/actions/runs/43070903822) | Green, 69 tests | Running the scanner as the caller fixed archive/cache/output permissions. Checker 15/0/0; CI SBOM, scan and accepted-image artifacts uploaded. |
| [PR regression](https://github.com/Ferasmich/fulfillops/actions/runs/43071282696) | Red, two failed tests | The deliberate permissive integer check accepted true. Tests rejected it; no accepted-image artifact was produced. |
| [PR fix](https://github.com/Ferasmich/fulfillops/actions/runs/43071728762) | Green, 70 tests | Strict validation restored; dedicated regression now covers both booleans. Checker 15/0/0; SBOM/scan/artifacts passed. |

[PR #1](https://github.com/Ferasmich/fulfillops/pull/1) is open for review and has not been merged. Main never contained the deliberate quantity bug. The PR's final code difference expands the regression test. Main has 69 tests; the PR has 70.

## Accepted image

The green main run built `fulfillops:3371a8195781cc84a5ee3ec6e06e00576f46655a`.

Image ID: `sha256:892224c78945c49747981441cf1cae28f6ad325fcc43373f8a496ac6e1ca6d10`.

Its accepted-image artifact ID is `13877447681`, with GitHub archive digest `sha256:20f6188b69b250a3c13c9100e843f6aa0c6c7acc428325bf0996637ef249d808`. The archive digest is not a container registry digest. The image tar and metadata were downloaded to `evid/06-ci/github/baseline-green/accepted-image/`; the large tar is kept locally and ignored by Git. GitHub's accepted-image artifact retention is seven days; quality evidence retention is 30 days, with local copies preserved here.

The image was published as a GitHub build artifact, not pushed to a container registry. Registry promotion remains a separate manual action. The workflow checks image identity/source commit before promotion; that registry path has not been exercised.

## Security evidence

The green main CI run produced a CycloneDX SBOM with 124 components and a real OS/Python vulnerability report. The documented gate passed with zero fixable High/Critical blockers and 351 informational findings, including unfixed High/Critical records. A green gate does not mean vulnerability-free. The raw results remain visible.

This is actual CI proof, separate from the temporary-copy regression demo in Part 4. The failed PR artifact list contains no accepted-image artifact. Every run's publication job was skipped. No release or cluster deployment was performed.

Logs, JUnit output, SBOM, scans and artifact metadata are under `evid/06-ci/github/`. See `summary.json` for run/source IDs and outcomes. The early failed baseline is retained as real environment troubleshooting, not confused with the deliberate regression.
