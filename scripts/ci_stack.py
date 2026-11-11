"""Run the built image and supplied checker on a fresh private Compose stack."""

import os
import subprocess
import sys
from uuid import uuid4

from common.config import ROOT
from scripts.verify_containers import free_port


def main():
    output = ROOT / "evid/06-ci"
    output.mkdir(parents=True, exist_ok=True)
    api_port, db_port = free_port(), free_port()
    while api_port == db_port:
        db_port = free_port()
    env = {
        **os.environ,
        "APP_ENV": "test",
        "POSTGRES_DB": "fulfillops_test_ci_stack",
        "API_PORT": str(api_port),
        "POSTGRES_PORT": str(db_port),
    }
    compose = ["docker", "compose", "-p", "fulfillops-ci-" + uuid4().hex[:8]]
    with (output / "container-check.log").open("w") as log:

        def run(command):
            result = subprocess.run(
                command,
                check=False,
                cwd=ROOT,
                env=env,
                capture_output=True,
                text=True,
                timeout=180,
            )
            log.write(
                "$ "
                + " ".join(command)
                + "\n"
                + result.stdout
                + result.stderr
                + f"\nExit code: {result.returncode}\n"
            )
            log.flush()
            return result

        try:
            start = run(
                compose + ["up", "-d", "--no-build", "--wait", "--wait-timeout", "90"]
            )
            if start.returncode:
                run(compose + ["logs", "init", "api", "worker"])
                return start.returncode
            run(compose + ["ps", "--all"])
            checker = run(
                [
                    sys.executable,
                    "assessment/fulfillops_public_checker.py",
                    "--base-url",
                    f"http://127.0.0.1:{api_port}",
                    "--concurrency",
                    "--stress",
                ]
            )
            (output / "public-checker.txt").write_text(checker.stdout + checker.stderr)
            return (
                checker.returncode
                if "15 passed / 0 failed / 0 skipped" in checker.stdout
                else 1
            )
        finally:
            cleanup = run(compose + ["down", "--volumes", "--remove-orphans"])
            if cleanup.returncode:
                raise RuntimeError("Private CI stack cleanup failed")


if __name__ == "__main__":
    raise SystemExit(main())
