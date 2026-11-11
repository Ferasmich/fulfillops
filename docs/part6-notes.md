# Part 6 — CI and supply-chain checks

Status: live quality workflow and red-to-green PR proof completed. See `docs/ci-live-results.md` and `evid/06-ci/github/`. Registry publication remains disabled; PR #1 is open and unmerged.

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

These local results were followed by real GitHub runs: main passed 69 tests and the corrected PR passed 70. CI-produced SBOM/scan and accepted-image artifacts are saved with source commits and run URLs in `docs/ci-live-results.md`. No registry digest has been published. Earlier local image metadata remains a historical snapshot.

## GitHub result and remaining release steps

The initial implementation and scanner fix are pushed to main. PR #1 records the intentional failure and corrected green run. Its test expansion is open for review. The baseline green accepted image and CI quality artifacts were downloaded before expiry.

Branch protection/release-review settings have not been changed. Configure them before relying on protected merges. Registry publication needs separate owner approval and a manual dispatch on main with publish enabled. No cluster deployment is included yet.

## Questions to prepare for

- **Why CI if tests already pass locally?** It repeats checks in a clean shared environment on proposed changes.
- **What is an SBOM?** A machine-readable list of the components in the built image, not proof that they are safe.
- **What blocks promotion?** Required quality steps and the security policy; publication depends on that successful job.
- **Why are some High/Critical records informational?** This policy separates vendor-fixable findings from those without a reported fix. Unfixed does not mean safe; they remain visible for review.
- **Why promote an archive instead of rebuilding?** The published image must be the exact one that passed the checks.
- **SHA tag versus digest?** The tag identifies a source revision by convention; the digest identifies image content.
- **Why no token on PR checks?** Tests/scans do not need registry-write privileges, especially for untrusted PR code.
