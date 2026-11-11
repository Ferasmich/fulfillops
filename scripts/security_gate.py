"""Enforce the documented policy against real Trivy JSON and CycloneDX output."""

import argparse
import json
from pathlib import Path


def assess(scan, sbom):
    if (
        not isinstance(scan, dict)
        or scan.get("SchemaVersion") != 2
        or not isinstance(scan.get("Results"), list)
        or not scan["Results"]
    ):
        raise ValueError("Missing or unsupported scan results")
    if (
        not isinstance(sbom, dict)
        or sbom.get("bomFormat") != "CycloneDX"
        or not isinstance(sbom.get("components"), list)
        or not sbom["components"]
    ):
        raise ValueError("Missing or empty CycloneDX SBOM")
    if not any(r.get("Class") == "lang-pkgs" for r in scan["Results"]):
        raise ValueError("Python/library dependency scan results missing")
    if not any(r.get("Class") == "os-pkgs" for r in scan["Results"]):
        raise ValueError("OS dependency scan results missing")
    blocking, informational = [], []
    for result in scan["Results"]:
        for finding in result.get("Vulnerabilities") or []:
            if not all(
                isinstance(finding.get(k), str) and finding[k]
                for k in ("VulnerabilityID", "PkgName", "Severity", "InstalledVersion")
            ):
                raise ValueError("Incomplete vulnerability record")
            severity = finding["Severity"]
            if severity not in {"UNKNOWN", "LOW", "MEDIUM", "HIGH", "CRITICAL"}:
                raise ValueError("Unsupported vulnerability severity")
            row = {
                k: finding.get(k, "")
                for k in (
                    "VulnerabilityID",
                    "PkgName",
                    "Severity",
                    "InstalledVersion",
                    "FixedVersion",
                )
            }
            row["target"] = result.get("Target", "")
            if severity in {"HIGH", "CRITICAL"} and str(row["FixedVersion"]).strip():
                blocking.append(row)
            else:
                informational.append(row)
    return {
        "passed": not blocking,
        "blocking": blocking,
        "informational": informational,
        "policy": "Block HIGH/CRITICAL with a vendor fix; retain other findings as informational",
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("scan", type=Path)
    parser.add_argument("sbom", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = assess(
            json.loads(args.scan.read_text()), json.loads(args.sbom.read_text())
        )
    except (OSError, ValueError, TypeError, AttributeError) as exc:
        report = {"passed": False, "error": str(exc)}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(
        "Security gate:",
        "PASS" if report["passed"] else "FAIL",
        "blocking:",
        len(report.get("blocking", [])),
        "informational:",
        len(report.get("informational", [])),
    )
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
