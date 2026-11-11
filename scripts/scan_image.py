"""Scan a saved image without mounting the Docker socket or project secrets."""

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from common.config import ROOT


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", default="fulfillops:local")
    parser.add_argument("--output", type=Path, default=ROOT / "evid/06-ci")
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    for generated in ("image.cdx.json", "vulnerabilities.json", "security-gate.json"):
        (out / generated).unlink(missing_ok=True)
    scanner = (ROOT / ".github/trivy-image.txt").read_text().strip()
    cache = (
        Path(os.environ.get("XDG_CACHE_HOME", str(Path.home() / ".cache")))
        / "fulfillops-trivy"
    )
    cache.mkdir(parents=True, exist_ok=True)
    with (out / "scan.log").open("w") as log:

        def run(command):
            log.write("$ " + " ".join(command) + "\n")
            log.flush()
            result = subprocess.run(
                command, check=False, stdout=log, stderr=subprocess.STDOUT, timeout=600
            )
            log.write(f"Exit code: {result.returncode}\n")
            log.flush()
            if result.returncode:
                raise RuntimeError("Scanner operation failed; inspect scan.log")

        inspect = subprocess.run(
            ["docker", "image", "inspect", args.image],
            check=True,
            capture_output=True,
            text=True,
        )
        image = json.loads(inspect.stdout)[0]
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=False,
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        (out / "image-metadata.json").write_text(
            json.dumps(
                {
                    "tag": args.image,
                    "image_id": image["Id"],
                    "source_commit": commit.stdout.strip()
                    if commit.returncode == 0
                    else None,
                    "scanner": scanner,
                },
                indent=2,
            )
            + "\n"
        )
        with tempfile.TemporaryDirectory(prefix="fulfillops-scan-") as directory:
            archive = Path(directory) / "image.tar"
            run(["docker", "save", "--output", str(archive), args.image])
            base = [
                "docker",
                "run",
                "--rm",
                "--user",
                f"{os.getuid()}:{os.getgid()}",
                "--cap-drop=ALL",
                "--security-opt=no-new-privileges",
                "--read-only",
                "--tmpfs",
                "/tmp",
                "-v",
                str(Path(directory)) + ":/input:ro",
                "-v",
                str(out) + ":/output",
                "-v",
                str(cache.resolve()) + ":/cache",
                scanner,
                "image",
                "--cache-dir",
                "/cache",
                "--timeout",
                "8m",
                "--input",
                "/input/image.tar",
            ]
            run(base + ["--format", "cyclonedx", "--output", "/output/image.cdx.json"])
            run(
                base
                + [
                    "--scanners",
                    "vuln",
                    "--format",
                    "json",
                    "--output",
                    "/output/vulnerabilities.json",
                ]
            )
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "scripts.security_gate",
                str(out / "vulnerabilities.json"),
                str(out / "image.cdx.json"),
                "--output",
                str(out / "security-gate.json"),
            ],
            check=False,
            cwd=ROOT,
            stdout=log,
            stderr=subprocess.STDOUT,
        )
        log.write(f"Gate exit code: {result.returncode}\n")
    print("SBOM, scan and gate report saved to", out)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
