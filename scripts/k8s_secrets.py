"""Create lab credentials in the explicit local cluster; never print values."""

import json
import secrets
import subprocess

from common.config import ROOT, settings

CONTEXT = "kind-fulfillops"


def run(args, payload=None):
    return subprocess.run(
        ["kubectl", "--context", CONTEXT, *args],
        check=False,
        input=json.dumps(payload) if payload else None,
        capture_output=True,
        text=True,
    )


def main():
    namespace = "fulfillops"
    probe = run(["get", "namespace", namespace, "--ignore-not-found", "-o", "name"])
    if probe.returncode:
        raise SystemExit("Cannot reach the explicit local cluster")
    if not probe.stdout.strip():
        result = run(["create", "namespace", namespace])
        if result.returncode:
            raise SystemExit("Cannot create local application namespace")
    existing = run(
        [
            "-n",
            namespace,
            "get",
            "secret",
            "fulfillops-db-credentials",
            "--ignore-not-found",
            "-o",
            "name",
        ]
    )
    if existing.returncode:
        raise SystemExit("Cannot inspect local credentials; no changes made")
    if existing.stdout.strip():
        print("Cluster credentials already exist; unchanged")
        return
    env = settings()
    keys = {
        "owner-password": "K8S_OWNER_PASSWORD",
        "api-password": "K8S_API_PASSWORD",
        "worker-password": "K8S_WORKER_PASSWORD",
    }
    missing = [name for name in keys.values() if not env.get(name)]
    pvc = run(
        [
            "-n",
            namespace,
            "get",
            "pvc",
            "postgres-data",
            "--ignore-not-found",
            "-o",
            "name",
        ]
    )
    if pvc.returncode:
        raise SystemExit("Cannot inspect persistent storage; no credentials generated")
    if missing and pvc.stdout.strip():
        raise SystemExit(
            "PVC exists but credentials are missing: restore the original local credentials first"
        )
    path = ROOT / ".env"
    text = path.read_text() if path.exists() else ""
    for name in missing:
        env[name] = secrets.token_hex(24)
        text += "\n" + name + "=" + env[name] + "\n"
    if missing:
        path.write_text(text)
        path.chmod(0o600)
    payload = {
        "apiVersion": "v1",
        "kind": "Secret",
        "metadata": {"name": "fulfillops-db-credentials", "namespace": namespace},
        "type": "Opaque",
        "stringData": {key: env[name] for key, name in keys.items()},
    }
    if run(["create", "-f", "-"], payload).returncode:
        raise SystemExit("Cluster credential creation failed; no values were printed")
    print(
        "Local cluster credentials created; values stay in ignored .env and Kubernetes, outside Git"
    )


if __name__ == "__main__":
    main()
