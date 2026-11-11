# Part 6 evidence — local verification

Verified locally on 11 November 2026. Live CI evidence is still pending.

- [Local tests](local-tests.txt), [JUnit](local-tests.xml): **69 passed**; Ruff/formatting passed; one upstream TestClient deprecation warning.
- [Workflow validation](workflow-validation.txt): actionlint passed.
- [Built-container check](container-check.log) and [public checker](public-checker.txt): **15 passed / 0 failed / 0 skipped**.
- [CycloneDX SBOM](image.cdx.json): 124 components.
- [Real vulnerability scan](vulnerabilities.json), [scan log](scan.log), [gate report](security-gate.json): zero blockers under the policy and 351 informational findings. Includes 96 High/two Critical records without reported vendor fixes; these are not hidden.
- [Image metadata](image-metadata.json): the actual local image ID and pinned scanner; source commit is null because no commit exists yet.
- [Blocking-path fixture](policy-block-demo.txt): explicitly synthetic, expected exit 1. Not a real CVE and not a GitHub pipeline.
- [Local summary](local-summary.json).

[Policy](../../docs/security-policy.md) and [Part 6 notes](../../docs/part6-notes.md) explain the choices. Local files do not replace a CI-generated SBOM, PR/run URLs, red-to-green proof or a published immutable image reference. Those remain pending until the project is committed/pushed and publication is approved.
