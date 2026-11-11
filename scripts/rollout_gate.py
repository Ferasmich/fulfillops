"""Require the expected Git revision and a fully healthy two-replica API release."""

import argparse
import json
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path


def kube_json(namespace, kind, name):
    command = [
        "kubectl",
        "--context",
        "kind-fulfillops",
        "-n",
        namespace,
        "get",
        kind,
        name,
        "-o",
        "json",
    ]
    return json.loads(subprocess.check_output(command, text=True))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--expected-revision", required=True)
    parser.add_argument("--release", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--timeout", type=float, default=150)
    args = parser.parse_args()
    deadline = time.monotonic() + args.timeout
    while True:
        app = kube_json("argocd", "application", "fulfillops")
        deployment = kube_json("fulfillops", "deployment", "fulfillops-api")
        state = deployment.get("status", {})
        current = (
            deployment["spec"]["template"]["metadata"]
            .get("annotations", {})
            .get("fulfillops.io/release")
        )
        source = app.get("status", {}).get("sync", {})
        expected = (
            current == args.release and source.get("revision") == args.expected_revision
        )
        observed = (
            state.get("observedGeneration", 0) >= deployment["metadata"]["generation"]
        )
        expired = any(
            c["type"] == "Progressing" and c.get("reason") == "ProgressDeadlineExceeded"
            for c in state.get("conditions", [])
        )
        counts = {
            name: state.get(name, 0)
            for name in [
                "replicas",
                "updatedReplicas",
                "readyReplicas",
                "availableReplicas",
            ]
        }
        healthy = (
            expected
            and observed
            and deployment["spec"]["replicas"] == 2
            and all(value == 2 for value in counts.values())
            and source.get("status") == "Synced"
            and app.get("status", {}).get("health", {}).get("status") == "Healthy"
            and app.get("status", {}).get("operationState", {}).get("phase")
            == "Succeeded"
        )
        if (
            healthy
            or (expected and observed and expired)
            or time.monotonic() >= deadline
        ):
            report = {
                "time": datetime.now(UTC).isoformat(),
                "passed": healthy,
                "expected_revision": args.expected_revision,
                "observed_revision": source.get("revision"),
                "expected_release": args.release,
                "observed_release": current,
                "sync": source.get("status"),
                "health": app.get("status", {}).get("health", {}).get("status"),
                "replicas": counts,
                "conditions": state.get("conditions", []),
                "reason": "healthy"
                if healthy
                else "ProgressDeadlineExceeded"
                if expired
                else "timeout",
            }
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(report, indent=2) + "\n")
            print(json.dumps(report, indent=2))
            return 0 if healthy else 1
        time.sleep(1)


if __name__ == "__main__":
    raise SystemExit(main())
