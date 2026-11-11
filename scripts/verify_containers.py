"""Verify Compose using a private disposable project, ports and volume."""

import json
import os
import socket
import subprocess
import sys
import time
from uuid import uuid4

import httpx

from common.config import ROOT, settings


def free_port():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def main():
    output = ROOT / "evid/05-containers"
    output.mkdir(parents=True, exist_ok=True)
    project = "fulfillops-check-" + uuid4().hex[:8]
    port, db_port = free_port(), free_port()
    while db_port == port:
        db_port = free_port()
    username = settings().get("POSTGRES_USER", "fulfillops")
    env = {
        **os.environ,
        "POSTGRES_DB": "fulfillops_test_containers",
        "APP_ENV": "test",
        "API_PORT": str(port),
        "POSTGRES_PORT": str(db_port),
        "FULFILLOPS_IMAGE": "fulfillops:local",
    }
    compose = ["docker", "compose", "-p", project]
    with (output / "compose-verification.txt").open("w") as log:

        def command(args, expected=0):
            run = subprocess.run(
                args,
                check=False,
                cwd=ROOT,
                env=env,
                capture_output=True,
                text=True,
                timeout=180,
            )
            log.write(
                "$ "
                + " ".join(args)
                + "\n"
                + run.stdout
                + run.stderr
                + f"\nExit code: {run.returncode}\n"
            )
            log.flush()
            if run.returncode != expected:
                raise RuntimeError("Unexpected command result: " + " ".join(args))
            return run.stdout

        def note(text):
            print(text, flush=True)
            log.write(text + "\n")
            log.flush()

        try:
            command(compose + ["build", "--no-cache", "api"])
            command(
                [
                    "docker",
                    "build",
                    "--no-cache",
                    "-f",
                    "Dockerfile.baseline",
                    "-t",
                    "fulfillops:baseline",
                    ".",
                ]
            )
            sizes = {}
            for image in ["fulfillops:local", "fulfillops:baseline"]:
                sizes[image] = int(
                    command(
                        ["docker", "image", "inspect", "--format", "{{.Size}}", image]
                    ).strip()
                )
            sizes["saved_bytes"] = (
                sizes["fulfillops:baseline"] - sizes["fulfillops:local"]
            )
            (output / "image-sizes.json").write_text(json.dumps(sizes, indent=2) + "\n")
            note(
                "Measured image sizes (local uncompressed bytes): " + json.dumps(sizes)
            )
            command(compose + ["up", "-d", "--build", "--wait", "--wait-timeout", "90"])
            note("Private Compose project started: " + project)
            command(compose + ["ps", "--all"])
            for service in ["api", "worker"]:
                command(compose + ["exec", "-T", service, "id"])
            command(
                compose
                + [
                    "exec",
                    "-T",
                    "api",
                    "python",
                    "-c",
                    "import importlib.util; from pathlib import Path; assert importlib.util.find_spec('pytest') is None; assert not Path('/app/.env').exists(); assert not Path('/app/.git').exists(); print('No test tools, local secrets or Git metadata in runtime image')",
                ]
            )
            command(
                compose
                + [
                    "exec",
                    "-T",
                    "worker",
                    "python",
                    "-c",
                    "from common.database import connect\nimport psycopg\nc=connect()\nprint('Role:',c.execute('SELECT current_user AS role').fetchone()['role'])\ntry:\n    c.execute(\"UPDATE products SET available=available WHERE sku='KIT-100'\")\nexcept psycopg.errors.InsufficientPrivilege:\n    print('Worker inventory update denied as expected')\nelse:\n    c.rollback()\n    raise SystemExit('Unexpected privilege')\nfinally:\n    c.close()\n",
                ]
            )
            command(
                compose
                + [
                    "exec",
                    "-T",
                    "api",
                    "python",
                    "-c",
                    "from common.database import connect\nimport psycopg\nc=connect()\nprint('Role:',c.execute('SELECT current_user AS role').fetchone()['role'])\ntry:\n    c.execute('CREATE TABLE forbidden_probe (id int)')\nexcept psycopg.errors.InsufficientPrivilege:\n    print('API DDL denied as expected')\nelse:\n    c.rollback()\n    raise SystemExit('Unexpected privilege')\nfinally:\n    c.close()\n",
                ]
            )
            command(
                compose
                + [
                    "run",
                    "--rm",
                    "--no-deps",
                    "-e",
                    "APP_ENV=production",
                    "init",
                    "python",
                    "-m",
                    "db.manage",
                    "reset-test",
                    "--confirm-test-reset",
                ],
                expected=1,
            )
            checker = [
                sys.executable,
                "assessment/fulfillops_public_checker.py",
                "--base-url",
                f"http://127.0.0.1:{port}",
                "--concurrency",
                "--stress",
            ]
            checker_result = command(checker)
            (output / "public-checker.txt").write_text(
                "$ " + " ".join(checker) + "\n" + checker_result
            )
            assert "15 passed / 0 failed / 0 skipped" in checker_result
            with httpx.Client(base_url=f"http://127.0.0.1:{port}", timeout=10) as http:
                response = http.post(
                    "/api/v1/orders",
                    headers={"Idempotency-Key": "container-persist-001"},
                    json={
                        "customer_id": "CUST-LAB",
                        "items": [{"sku": "KIT-100", "quantity": 1}],
                    },
                )
                assert response.status_code == 202
                receipt = response.json()
                until = time.monotonic() + 15
                while time.monotonic() < until:
                    order = http.get("/api/v1/orders/" + receipt["order_id"]).json()
                    if order["status"] == "completed":
                        break
                    time.sleep(0.1)
                assert order["status"] == "completed"
                stock = http.get("/api/v1/inventory/KIT-100").json()
            note("Before restart: " + json.dumps({"order": order, "stock": stock}))
            command(compose + ["restart", "api", "worker"])
            command(compose + ["down"])
            command(compose + ["up", "-d", "--wait", "--wait-timeout", "90"])
            with httpx.Client(base_url=f"http://127.0.0.1:{port}", timeout=10) as http:
                restored = http.get("/api/v1/orders/" + receipt["order_id"]).json()
                restored_stock = http.get("/api/v1/inventory/KIT-100").json()
                replay = http.post(
                    "/api/v1/orders",
                    headers={"Idempotency-Key": "container-persist-001"},
                    json={
                        "customer_id": "CUST-LAB",
                        "items": [{"sku": "KIT-100", "quantity": 1}],
                    },
                ).json()
            assert restored == order and restored_stock == stock and replay == receipt
            note(
                "After full down/up (volume retained): "
                + json.dumps(
                    {"order": restored, "stock": restored_stock, "replay": replay}
                )
            )
            for service in ["api", "worker"]:
                ids = command(compose + ["ps", "-q", service]).split()
                for container in ids:
                    command(
                        [
                            "docker",
                            "inspect",
                            "--format",
                            "{{.Name}} user={{.Config.User}} read_only={{.HostConfig.ReadonlyRootfs}} health={{.State.Health.Status}}",
                            container,
                        ]
                    )
            command(compose + ["stop", "api", "worker"])
            command(
                compose
                + [
                    "run",
                    "--rm",
                    "--no-deps",
                    "init",
                    "python",
                    "-m",
                    "db.manage",
                    "reset-test",
                    "--confirm-test-reset",
                ]
            )
            command(
                compose
                + [
                    "exec",
                    "-T",
                    "db",
                    "psql",
                    "-U",
                    username,
                    "-d",
                    "fulfillops_test_containers",
                    "-P",
                    "pager=off",
                    "-c",
                    "SELECT sku, available FROM products ORDER BY sku;",
                ]
            )
            note(
                "PASS: checker, non-root runtime, privilege checks, persistence/replay, safe reset"
            )
        finally:
            # Only this script's uniquely named project and its private test volume are removed.
            command(compose + ["down", "--volumes", "--remove-orphans"])


if __name__ == "__main__":
    main()
