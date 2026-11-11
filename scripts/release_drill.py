"""Owned kind-lab Git release exercise. Requires explicit consent to Git pushes."""

import argparse
import json
import re
import signal
import socket
import subprocess
import sys
import time
from datetime import UTC, datetime

import httpx

from common.config import ROOT


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--candidate",
        required=True,
        help="CI-passed application source commit, preloaded in kind",
    )
    parser.add_argument("--confirm-lab-git-push", action="store_true")
    args = parser.parse_args()
    if not args.confirm_lab_git_push or not re.fullmatch(
        r"[0-9a-f]{40}", args.candidate
    ):
        parser.error(
            "Explicit lab Git-push confirmation and full candidate SHA are required"
        )
    if (
        subprocess.check_output(
            ["git", "branch", "--show-current"], cwd=ROOT, text=True
        ).strip()
        != "main"
    ):
        raise SystemExit("Run only on main in the owned lab repository")
    subprocess.run(["git", "diff", "--exit-code"], check=True, cwd=ROOT)
    runs = json.loads(
        subprocess.check_output(
            [
                "gh",
                "run",
                "list",
                "--workflow",
                "ci.yml",
                "--commit",
                args.candidate,
                "--json",
                "conclusion,event,url",
            ],
            cwd=ROOT,
            text=True,
        )
    )
    assert any(r["conclusion"] == "success" and r["event"] == "push" for r in runs), (
        "Candidate must pass real CI before promotion"
    )
    out = ROOT / "evid/08-reliability"
    out.mkdir(parents=True, exist_ok=True)
    state = {"candidate": args.candidate, "candidate_ci": runs, "events": []}
    bad_commit = None
    recovery_commit = None
    recovered = False
    processes = []
    with (out / "release-drill.txt").open("w") as log:

        def record(event, **fields):
            row = {"time": datetime.now(UTC).isoformat(), "event": event, **fields}
            state["events"].append(row)
            (out / "release-summary.json").write_text(
                json.dumps(state, indent=2) + "\n"
            )
            print(json.dumps(row), flush=True)
            log.write(json.dumps(row) + "\n")
            log.flush()

        def run(command, expected=0, timeout=180):
            result = subprocess.run(
                command,
                cwd=ROOT,
                check=False,
                capture_output=True,
                text=True,
                timeout=timeout,
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
            if result.returncode != expected:
                raise RuntimeError("Unexpected command result: " + " ".join(command))
            return result.stdout

        def kube(*command):
            return run(["kubectl", "--context", "kind-fulfillops", *command])

        def get(namespace, kind, name=None):
            return json.loads(
                kube(
                    "-n",
                    namespace,
                    "get",
                    kind,
                    *([name] if name else []),
                    "-o",
                    "json",
                )
            )

        def database():
            query = "SELECT json_build_object('orders',(SELECT json_agg(o ORDER BY id) FROM (SELECT id,status,total_cents FROM orders) o),'receipts',(SELECT json_agg(order_id ORDER BY order_id) FROM completion_receipts),'inventory',(SELECT json_object_agg(sku,available) FROM products))"
            return json.loads(
                kube(
                    "-n",
                    "fulfillops",
                    "exec",
                    "postgres-0",
                    "--",
                    "psql",
                    "-U",
                    "fulfillops",
                    "-d",
                    "fulfillops_test_k8s",
                    "-t",
                    "-A",
                    "-c",
                    query,
                )
            )

        def capture(phase):
            for namespace, kind, name in [
                ("argocd", "application", "fulfillops"),
                ("fulfillops", "deployment", "fulfillops-api"),
            ]:
                (out / f"{phase}-{kind}.json").write_text(
                    json.dumps(get(namespace, kind, name), indent=2) + "\n"
                )
            pods = json.loads(
                kube(
                    "-n",
                    "fulfillops",
                    "get",
                    "pods",
                    "-l",
                    "app=fulfillops-api",
                    "-o",
                    "json",
                )
            )
            (out / f"{phase}-pods.json").write_text(json.dumps(pods, indent=2) + "\n")
            endpoints = json.loads(
                kube(
                    "-n",
                    "fulfillops",
                    "get",
                    "endpointslices",
                    "-l",
                    "kubernetes.io/service-name=fulfillops-api",
                    "-o",
                    "json",
                )
            )
            (out / f"{phase}-endpoints.json").write_text(
                json.dumps(endpoints, indent=2) + "\n"
            )
            for pod in pods["items"]:
                name = pod["metadata"]["name"]
                if pod["status"].get("phase") != "Running":
                    continue
                metrics = kube(
                    "-n",
                    "fulfillops",
                    "exec",
                    name,
                    "--",
                    "python",
                    "-c",
                    "import urllib.request; print(urllib.request.urlopen('http://127.0.0.1:8080/metrics',timeout=3).read().decode())",
                )
                (out / f"{phase}-{name}.prom").write_text(metrics)
                (out / f"{phase}-{name}.log").write_text(
                    kube("-n", "fulfillops", "logs", name, "--tail=1200")
                )
            return pods, endpoints

        def commit(message, paths):
            run(["git", "add", *paths])
            run(["git", "commit", "-m", message])
            return run(["git", "rev-parse", "HEAD"]).strip()

        def publish():
            run(["git", "push", "origin", "main"])
            kube(
                "-n",
                "argocd",
                "annotate",
                "application",
                "fulfillops",
                "argocd.argoproj.io/refresh=hard",
                "--overwrite",
            )

        def gate(revision, release, phase, expected=0):
            run(
                [
                    sys.executable,
                    "-m",
                    "scripts.rollout_gate",
                    "--expected-revision",
                    revision,
                    "--release",
                    release,
                    "--output",
                    str(out / (phase + "-gate.json")),
                ],
                expected=expected,
            )

        def probe(phase, duration):
            stream = (out / (phase + "-probe.log")).open("w")
            command = [
                sys.executable,
                "assessment/fulfillops_rollout_probe.py",
                "--base-url",
                base,
                "--duration",
                str(duration),
                "--interval",
                "0.25",
                "--output",
                str(out / (phase + "-rollout.csv")),
            ]
            stream.write("$ " + " ".join(command) + "\n")
            stream.flush()
            process = subprocess.Popen(command, cwd=ROOT, stdout=stream, stderr=stream)
            processes.append((process, stream))
            time.sleep(1)
            return process

        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            port = sock.getsockname()[1]
        base = f"http://127.0.0.1:{port}"
        forward_log = (out / "stable-proxy-forward.log").open("w")
        forward = subprocess.Popen(
            [
                "kubectl",
                "--context",
                "kind-fulfillops",
                "-n",
                "fulfillops",
                "port-forward",
                "--address",
                "127.0.0.1",
                "pod/fulfillops-probe",
                f"{port}:8080",
            ],
            stdout=forward_log,
            stderr=forward_log,
        )
        try:
            for _ in range(60):
                try:
                    if httpx.get(base + "/health/ready", timeout=2).status_code == 200:
                        break
                except httpx.TransportError:
                    pass
                time.sleep(0.5)
            else:
                raise RuntimeError("Stable probe is not reachable")
            before = database()
            assert before["orders"], (
                "Preserve a real committed lab order before testing"
            )
            (out / "orders-before.json").write_text(json.dumps(before, indent=2) + "\n")
            record(
                "baseline",
                orders=len(before["orders"]),
                source_revision=get("argocd", "application", "fulfillops")["status"][
                    "sync"
                ]["revision"],
            )
            capture("before")
            marker = "part8-good-" + datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
            paths = [
                "infra/k8s/api.yaml",
                "infra/k8s/worker.yaml",
                "infra/k8s/bootstrap.yaml",
            ]
            for file in paths:
                p = ROOT / file
                p.write_text(
                    re.sub(
                        r"image: fulfillops:[0-9a-f]{40}",
                        "image: fulfillops:" + args.candidate,
                        p.read_text(),
                    )
                )
            api = ROOT / paths[0]
            text = api.read_text()
            if "fulfillops.io/release:" in text:
                text = re.sub(
                    r"fulfillops.io/release: .+",
                    "fulfillops.io/release: " + marker,
                    text,
                )
            else:
                text = text.replace(
                    "    metadata:\n      labels:",
                    "    metadata:\n      annotations:\n        fulfillops.io/release: "
                    + marker
                    + "\n      labels:",
                )
            if "lifecycle:" not in text:
                text = text.replace(
                    "          startupProbe:",
                    '          lifecycle:\n            preStop:\n              exec:\n                command: [python, -c, "import time; time.sleep(3)"]\n          startupProbe:',
                )
            api.write_text(text)
            good_commit = commit(
                "Verify healthy local API rolling release",
                paths + ["scripts/rollout_gate.py", "scripts/release_drill.py"],
            )
            state["good_commit"] = good_commit
            healthy_probe = probe("good", 30)
            record("good_release_push", revision=good_commit, release=marker)
            publish()
            gate(good_commit, marker, "good")
            assert healthy_probe.wait(timeout=45) == 0, (
                "Healthy rollout probe observed a failure"
            )
            capture("good")
            record("healthy_rollout_passed", revision=good_commit)
            run(
                [
                    sys.executable,
                    "-m",
                    "scripts.http_samples",
                    "--base-url",
                    base,
                    "--samples",
                    "250",
                    "--output",
                    str(out / "http-samples.csv"),
                ]
            )
            capture("measured")
            text = api.read_text()
            assert text.count("path: /health/ready") == 1
            bad_marker = marker.replace("part8-good", "part8-bad")
            api.write_text(
                text.replace(
                    "path: /health/ready", "path: /health/forced-not-ready"
                ).replace(marker, bad_marker)
            )
            bad_commit = commit(
                "Exercise lab rollout rejection with invalid readiness path", [paths[0]]
            )
            state["bad_commit"] = bad_commit
            bad_probe = probe("bad", 120)
            record("bad_release_push", revision=bad_commit, release=bad_marker)
            publish()
            gate(bad_commit, bad_marker, "bad", expected=1)
            for _ in range(40):
                if (
                    get("argocd", "application", "fulfillops")["status"]["health"][
                        "status"
                    ]
                    == "Degraded"
                ):
                    break
                time.sleep(0.5)
            pods, endpoints = capture("bad")
            bad_pods = {
                p["metadata"]["name"]
                for p in pods["items"]
                if p["metadata"].get("annotations", {}).get("fulfillops.io/release")
                == bad_marker
            }
            ready_endpoints = {
                e["targetRef"]["name"]
                for s in endpoints["items"]
                for e in s.get("endpoints", [])
                if e.get("conditions", {}).get("ready")
            }
            assert bad_pods and not bad_pods.intersection(ready_endpoints)
            assert len(ready_endpoints) == 2
            assert (
                get("argocd", "application", "fulfillops")["status"]["health"]["status"]
                == "Degraded"
            )
            (out / "bad-events.txt").write_text(
                kube("-n", "fulfillops", "get", "events", "--sort-by=.lastTimestamp")
            )
            record(
                "unhealthy_release_blocked",
                revision=bad_commit,
                bad_pods=sorted(bad_pods),
                ready_endpoints=sorted(ready_endpoints),
            )
            run(["git", "revert", "--no-edit", bad_commit])
            recovery_commit = run(["git", "rev-parse", "HEAD"]).strip()
            state["recovery_commit"] = recovery_commit
            publish()
            record("git_revert_pushed", revision=recovery_commit, reverted=bad_commit)
            gate(recovery_commit, marker, "recovery")
            recovered = True
            assert bad_probe.wait(timeout=140) == 0, (
                "Availability probe observed a failure during broken release/recovery"
            )
            capture("recovery")
            after = database()
            assert before == after, "Committed data changed during release drills"
            (out / "orders-after.json").write_text(json.dumps(after, indent=2) + "\n")
            record(
                "recovered",
                revision=recovery_commit,
                committed_orders_preserved=len(after["orders"]),
                registry_publication=False,
            )
        finally:
            if bad_commit and not recovered:
                record("emergency_git_recovery", bad_commit=bad_commit)
                if recovery_commit is None:
                    run(["git", "revert", "--no-edit", bad_commit])
                publish()
            for process, stream in processes:
                if process.poll() is None:
                    process.wait(timeout=150)
                stream.close()
            forward.terminate()
            forward.wait(timeout=10)
            forward_log.close()


def interrupt(signum, frame):
    raise KeyboardInterrupt()


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, interrupt)
    main()
