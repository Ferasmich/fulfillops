# Security scan policy

The workflow scans the built runtime image with Trivy 0.76.2, pinned by image digest. The report covers Debian packages and installed Python dependencies. A CycloneDX JSON SBOM lists the image components.

## Blocking

- A HIGH or CRITICAL vulnerability with a vendor-reported fixed version.
- Missing, empty, malformed or unsupported scan/SBOM output.
- Missing OS or language-package scan coverage.
- A failed scanner command, test, lint check, container checker or build.

## Informational

LOW/MEDIUM/UNKNOWN findings and HIGH/CRITICAL findings without a reported vendor fix remain visible in the raw scan and gate report. They do not automatically fail this local-lab policy. This is a deliberate policy choice, not a claim that they are harmless. Review unfixed findings before any real production release and rescan when fixes become available.

Local scan on 11 November 2026: zero blocking and 351 informational findings: 109 LOW, 134 MEDIUM, 96 HIGH, two CRITICAL and ten UNKNOWN. The two Critical records were CVE-2025-7458 (`libsqlite3-0`) and CVE-2023-45853 (`zlib1g`), both with an empty fixed-version field. No finding is suppressed through an ignore list, and no exploitability assessment is claimed. The gate passed under this policy; the image is not vulnerability-free.

`python -m scripts.security_gate` returns a nonzero exit code when the policy fails. Unit tests and a labelled synthetic CLI fixture verify the blocking path. Synthetic records are never presented as actual image findings or live CI runs.

## Publication

PR/push checks have contents-read permissions. They never publish images. Manual workflow dispatch on `main`, with `publish=true`, is required for the publication job. That job depends on the successful quality job and downloads its accepted image rather than rebuilding it. It verifies the image ID and source commit before tagging/pushing. Existing SHA tags are refused. The registry digest is the final immutable content reference; SHA tags are a naming convention, not a promise of registry-level immutability.

Only publication gets packages-write access. Its token is passed to the pinned Docker login action, not printed or mounted into the scanner. The scanner receives only an exported image archive, an output directory and its public database cache; it has no Docker socket, project `.env` or repository mount.

Configure the `release` environment with required review if supported by the repository plan. Configure branch protection on `main` to require `quality-gate`; workflow files alone do not prevent a repository owner from bypassing merge rules. No protection or environment-review setting has been changed yet.

References: [Trivy SBOM](https://trivy.dev/docs/latest/supply-chain/sbom/), [Trivy 0.76.2](https://github.com/aquasecurity/trivy/releases/tag/v0.76.2), [GitHub secrets](https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/use-secrets).
