import pytest

from scripts.security_gate import assess

SBOM = {"bomFormat": "CycloneDX", "components": [{"name": "example"}]}


def scan(severity="HIGH", fixed="2.0"):
    return {
        "SchemaVersion": 2,
        "Results": [
            {"Class": "os-pkgs", "Vulnerabilities": []},
            {
                "Class": "lang-pkgs",
                "Vulnerabilities": [
                    {
                        "VulnerabilityID": "LAB-TEST-ONLY",
                        "PkgName": "example",
                        "Severity": severity,
                        "InstalledVersion": "1.0",
                        "FixedVersion": fixed,
                    }
                ],
            },
        ],
    }


@pytest.mark.parametrize("severity", ["HIGH", "CRITICAL"])
def test_fixed_high_critical_findings_block_promotion(severity):
    result = assess(scan(severity), SBOM)
    assert not result["passed"]
    assert len(result["blocking"]) == 1


@pytest.mark.parametrize(
    "severity,fixed",
    [
        ("LOW", "2.0"),
        ("MEDIUM", "2.0"),
        ("HIGH", ""),
        ("CRITICAL", ""),
        ("UNKNOWN", ""),
    ],
)
def test_informational_findings_remain_visible(severity, fixed):
    result = assess(scan(severity, fixed), SBOM)
    assert result["passed"]
    assert len(result["informational"]) == 1


@pytest.mark.parametrize("value", [{}, {"SchemaVersion": 2, "Results": []}])
def test_missing_scan_fails_closed(value):
    with pytest.raises(ValueError):
        assess(value, SBOM)


def test_empty_sbom_fails_closed():
    with pytest.raises(ValueError):
        assess(scan(), {"bomFormat": "CycloneDX", "components": []})


def test_missing_library_scan_fails_closed():
    value = scan()
    value["Results"] = value["Results"][:1]
    with pytest.raises(ValueError):
        assess(value, SBOM)
