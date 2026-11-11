# Part 6 — CI and supply-chain checks

Status: implemented and checked locally. Live GitHub runs and publication are still pending approval to commit/push. This part is not fully complete yet.

## Workflow

`.github/workflows/ci.yml` runs on pull requests to main, pushes to main and manual dispatch. It installs pinned packages, checks Python/workflow formatting, runs owned tests and the deliberate regression exercise, builds the image, runs the public checker against a fresh container stack, generates a CycloneDX SBOM and scans OS/Python dependencies. Any required failure stops the quality job and prevents accepted-image publication.

Evidence artifacts are uploaded even on a failure. The accepted image archive is uploaded only after all checks pass. CI clears pre-existing evidence inside its disposable checkout so old local reports cannot be mistaken for current CI results. Test database credentials are disposable lab-only values, not production secrets.

GitHub Actions are pinned to commit SHAs. Scanner/validator images are pinned by digest. Main/PR jobs have read-only repository permissions. The optional manual publication job gets packages-write access, verifies the exact accepted image, refuses an existing SHA tag and records its registry digest.

## Local results

- 69 tests passed, including 11 security-policy cases.
- Ruff and formatting passed; actionlint accepted the workflow.
- Built-container CI checker: 15 passed, no failures/skips.
- Real CycloneDX SBOM: 124 components.
- Real OS/Python scan: zero blockers under the documented policy, 351 informational findings including 96 High/two Critical without reported fixes.
- A labelled synthetic fixable High finding returned exit 1, proving the CLI blocking path.

These are local results. The SBOM is not yet a CI-produced artifact, there is no real red/green run URL and no registry digest has been published. Local image metadata records no source commit because the project has not been committed yet. Earlier Part 4 regression proof is separate from a red-to-green pipeline.

## Live steps after approval

1. Make an initial commit and push to main; check the real workflow and save its run URL/artifacts.
2. Create a demonstration feature branch and PR with the deliberate boolean-quantity bug. Save the failed run and show that no accepted-image artifact was produced.
3. Repair that branch and push the fix. Save the corrected green run and PR URL. Keep main free of the demonstration bug.
4. Configure the required quality check and release review as available; verify the actual settings.
5. Once the owner approves image publication, dispatch the workflow on main with publish enabled. Save the accepted image's SHA tag and registry digest. No cluster deployment is included yet.

## Questions to prepare for

- **Why CI if tests already pass locally?** It repeats checks in a clean shared environment on proposed changes.
- **What is an SBOM?** A machine-readable list of the components in the built image, not proof that they are safe.
- **What blocks promotion?** Required quality steps and the security policy; publication depends on that successful job.
- **Why are some High/Critical records informational?** This policy separates vendor-fixable findings from those without a reported fix. Unfixed does not mean safe; they remain visible for review.
- **Why promote an archive instead of rebuilding?** The published image must be the exact one that passed the checks.
- **SHA tag versus digest?** The tag identifies a source revision by convention; the digest identifies image content.
- **Why no token on PR checks?** Tests/scans do not need registry-write privileges, especially for untrusted PR code.
