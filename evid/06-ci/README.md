# Part 6 evidence

Verified locally and on GitHub on 11 November 2026.

## Live GitHub proof

[PR #1](https://github.com/Ferasmich/fulfillops/pull/1): [red run](https://github.com/Ferasmich/fulfillops/actions/runs/43071282696) then [green run](https://github.com/Ferasmich/fulfillops/actions/runs/43071728762). Red failed two tests and produced no accepted image; green passed 70 tests, the checker, SBOM/scan and artifact upload. [Main baseline](https://github.com/Ferasmich/fulfillops/actions/runs/43070903822) passed 69 tests.

- [Run/source/artifact summary](github/summary.json)
- [Green CI SBOM](github/baseline-green/artifacts/06-ci/image.cdx.json)
- [Green CI scan](github/baseline-green/artifacts/06-ci/vulnerabilities.json)
- [Failed PR metadata](github/pr-red/run.json), [artifact list](github/pr-red/artifacts.json)
- [Corrected PR metadata](github/pr-green/run.json), [JUnit](github/pr-green/artifacts/06-ci/tests.xml)
- [Live results and accepted-image identity](../../docs/ci-live-results.md)

All raw logs/downloaded quality artifacts are in `github/`. The accepted main image tar is saved locally but excluded from Git. PR is unmerged and registry publication was not triggered.

## Earlier local checks

- [Local tests](local-tests.txt), [JUnit](local-tests.xml): **69 passed**; Ruff/formatting passed; one upstream TestClient deprecation warning.
- [Workflow validation](workflow-validation.txt): actionlint passed.
- [Built-container check](container-check.log) and [public checker](public-checker.txt): **15 passed / 0 failed / 0 skipped**.
- [CycloneDX SBOM](image.cdx.json): 124 components.
- [Real vulnerability scan](vulnerabilities.json), [scan log](scan.log), [gate report](security-gate.json): zero blockers under the policy and 351 informational findings. Includes 96 High/two Critical records without reported vendor fixes; these are not hidden.
- [Image metadata](image-metadata.json): the actual local image ID and pinned scanner; source commit is null because no commit exists yet.
- [Blocking-path fixture](policy-block-demo.txt): explicitly synthetic, expected exit 1. Not a real CVE and not a GitHub pipeline.
- [Local summary](local-summary.json).

[Policy](../../docs/security-policy.md) and [Part 6 notes](../../docs/part6-notes.md) explain the choices. The live runs above now supply the CI-generated SBOM, PR/run URLs and red-to-green proof. Registry promotion is still a separate untested/manual release action.
