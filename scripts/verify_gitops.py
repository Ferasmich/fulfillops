"""Verify the owned kind lab: real Git sync, replicas, drift and persistent data."""

import argparse
import json
import socket
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import ExitStack, contextmanager
from datetime import UTC, datetime
from threading import Barrier
from uuid import UUID

import httpx

from common.config import ROOT

CONTEXT = "kind-fulfillops"
NAMESPACE = "fulfillops"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--repeat",
        action="store_true",
        help="Repeat drift/persistence on existing proof order, skipping checker/races",
    )
    args = parser.parse_args()
    out = ROOT / "evid/07-gitops"
    out.mkdir(parents=True, exist_ok=True)
    with (out / "verification.txt").open("w") as log:

        def record(message):
            stamp = datetime.now(UTC).isoformat()
            text = stamp + " " + message
            log.write(text + "\n")
            log.flush()
            print(text, flush=True)

        def kube(*command, quiet=False):
            result = subprocess.run(
                ["kubectl", "--context", CONTEXT, *command],
                check=False,
                capture_output=True,
                text=True,
                timeout=90,
            )
            if not quiet:
                log.write(
                    "$ kubectl --context "
                    + CONTEXT
                    + " "
                    + " ".join(command)
                    + "\n"
                    + result.stdout
                    + result.stderr
                    + f"Exit code: {result.returncode}\n"
                )
                log.flush()
            if result.returncode:
                raise RuntimeError("Local kubectl command failed: " + " ".join(command))
            return result.stdout

        def obj(namespace, kind, name):
            return json.loads(
                kube("-n", namespace, "get", kind, name, "-o", "json", quiet=True)
            )

        def save(name, value):
            (out / name).write_text(json.dumps(value, indent=2) + "\n")

        def wait_for(check, message, timeout=120):
            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline:
                if check():
                    return
                time.sleep(0.5)
            raise RuntimeError("Timed out: " + message)

        def app_ready():
            app = obj("argocd", "application", "fulfillops")
            return (
                app.get("status", {}).get("sync", {}).get("status") == "Synced"
                and app.get("status", {}).get("health", {}).get("status") == "Healthy"
            )

        def sql(query):
            return kube(
                "-n",
                NAMESPACE,
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
                quiet=True,
            ).strip()

        def snapshot(order_id):
            identifier = str(UUID(order_id))
            return json.loads(
                sql(
                    "SELECT json_build_object('order_id',o.id,'status',o.status,'total_cents',o.total_cents,'orders',(SELECT count(*) FROM orders),'receipts',(SELECT count(*) FROM completion_receipts),'stock',(SELECT available FROM products WHERE sku='KIT-100')) FROM orders o WHERE o.id='"
                    + identifier
                    + "'"
                )
            )

        @contextmanager
        def forward(pod):
            with socket.socket() as sock:
                sock.bind(("127.0.0.1", 0))
                port = sock.getsockname()[1]
            with (out / (pod + "-" + str(port) + "-forward.log")).open(
                "w"
            ) as transcript:
                process = subprocess.Popen(
                    [
                        "kubectl",
                        "--context",
                        CONTEXT,
                        "-n",
                        NAMESPACE,
                        "port-forward",
                        "--address",
                        "127.0.0.1",
                        "pod/" + pod,
                        f"{port}:8080",
                    ],
                    stdout=transcript,
                    stderr=transcript,
                )
                try:
                    url = f"http://127.0.0.1:{port}"

                    def reachable():
                        if process.poll() is not None:
                            raise RuntimeError("Pod port-forward exited")
                        try:
                            return (
                                httpx.get(url + "/health/ready", timeout=2).status_code
                                == 200
                            )
                        except httpx.TransportError:
                            return False

                    wait_for(reachable, "API pod forwarding", 30)
                    yield url
                finally:
                    process.terminate()
                    process.wait(timeout=10)

        record("Starting verification in explicit local context " + CONTEXT)
        if args.repeat:
            record(
                "Repeat mode: checker/races are skipped; reuse the existing proof order"
            )
        wait_for(app_ready, "initial GitOps health")
        app = obj("argocd", "application", "fulfillops")
        save("application-before.json", app)
        pods = json.loads(
            kube(
                "-n",
                NAMESPACE,
                "get",
                "pods",
                "-l",
                "app=fulfillops-api",
                "-o",
                "json",
                quiet=True,
            )
        )["items"]
        pod_names = sorted(p["metadata"]["name"] for p in pods)
        assert len(pod_names) == 2
        workers = json.loads(
            kube(
                "-n",
                NAMESPACE,
                "get",
                "pods",
                "-l",
                "app=fulfillops-worker",
                "-o",
                "json",
                quiet=True,
            )
        )["items"]
        assert len(workers) == 2
        assert all(
            all(c["ready"] for c in p["status"]["containerStatuses"])
            for p in pods + workers
        )
        endpoints = json.loads(
            kube(
                "-n",
                NAMESPACE,
                "get",
                "endpointslices",
                "-l",
                "kubernetes.io/service-name=fulfillops-api",
                "-o",
                "json",
                quiet=True,
            )
        )
        assert sum(len(s.get("endpoints", [])) for s in endpoints["items"]) == 2
        save("service-endpoints.json", endpoints)
        kube(
            "-n",
            NAMESPACE,
            "get",
            "deployment,statefulset,pods,services,pvc",
            "-o",
            "wide",
        )
        record(
            "Git revision "
            + app["status"]["sync"]["revision"]
            + "; two ready API pods and two ready worker pods"
        )
        payload = {
            "customer_id": "CUST-K8S",
            "items": [{"sku": "KIT-100", "quantity": 1}],
        }
        key = "k8s-shared-key-001"
        with ExitStack() as stack:
            urls = [stack.enter_context(forward(pod)) for pod in pod_names]
            if not args.repeat:
                assert sql("SELECT count(*) FROM orders") == "0", (
                    "Full checker requires a fresh lab dataset; use --repeat for existing proof"
                )
                stocks = json.loads(
                    sql("SELECT json_object_agg(sku,available) FROM products")
                )
                assert stocks == {"KIT-100": 7, "PART-200": 12, "PACK-300": 5}
                command = [
                    sys.executable,
                    "assessment/fulfillops_public_checker.py",
                    "--base-url",
                    urls[0],
                    "--concurrency",
                    "--stress",
                ]
                check = subprocess.run(
                    command,
                    check=False,
                    cwd=ROOT,
                    capture_output=True,
                    text=True,
                    timeout=90,
                )
                (out / "public-checker.txt").write_text(
                    "$ "
                    + " ".join(command)
                    + "\n"
                    + check.stdout
                    + check.stderr
                    + f"\nExit code: {check.returncode}\n"
                )
                assert (
                    check.returncode == 0
                    and "15 passed / 0 failed / 0 skipped" in check.stdout
                )
                record("Kubernetes public checker: 15 passed / 0 failed / 0 skipped")

                def race(keys):
                    barrier = Barrier(len(keys))

                    def submit(item):
                        i, request_key = item
                        barrier.wait(timeout=15)
                        response = httpx.post(
                            urls[i % 2] + "/api/v1/orders",
                            json=payload,
                            headers={"Idempotency-Key": request_key},
                            timeout=15,
                        )
                        return {
                            "pod": pod_names[i % 2],
                            "status": response.status_code,
                            "body": response.json(),
                        }

                    with ThreadPoolExecutor(max_workers=len(keys)) as pool:
                        return list(pool.map(submit, enumerate(keys)))

                same = race([key] * 8)
                assert all(x["status"] == 202 for x in same)
                ids = {x["body"]["order_id"] for x in same}
                assert len(ids) == 1
                order_id = ids.pop()
                assert (
                    json.loads(
                        sql("SELECT available FROM products WHERE sku='KIT-100'")
                    )
                    == 5
                )
                different = race([f"k8s-competing-{i:03}" for i in range(12)])
                assert sum(x["status"] == 202 for x in different) == 5
                assert sum(x["status"] == 409 for x in different) == 7
                assert all(
                    x["body"]["error"]["code"] == "OUT_OF_STOCK"
                    for x in different
                    if x["status"] == 409
                )
                save(
                    "cross-pod-races.json",
                    {"same_key": same, "different_keys": different},
                )
                record(
                    "Cross-pod races: eight same-key -> one ID/one decrement; 12 competing -> five accepted/seven rejected; KIT stock zero"
                )
            else:
                assert (
                    sql(
                        "SELECT count(*) FROM order_requests WHERE key='k8s-shared-key-001'"
                    )
                    == "1"
                ), "No previous proof order; run the fresh verification first"
                replay = httpx.post(
                    urls[0] + "/api/v1/orders",
                    json=payload,
                    headers={"Idempotency-Key": key},
                    timeout=10,
                )
                assert replay.status_code == 202
                order_id = replay.json()["order_id"]
            wait_for(
                lambda: (
                    sql("SELECT count(*) FROM orders WHERE status <> 'completed'")
                    == "0"
                ),
                "worker completions",
                20,
            )
            before = snapshot(order_id)
            assert (
                before["status"] == "completed"
                and before["orders"] == before["receipts"]
            )
            save("database-before.json", before)
            record("Database before drift/restart: " + json.dumps(before))
            pvc_before = obj(NAMESPACE, "pvc", "postgres-data")
            pg_before = obj(NAMESPACE, "pod", "postgres-0")["metadata"]["uid"]
            try:
                # Pause repair briefly so OutOfSync can be observed rather than missed.
                kube(
                    "-n",
                    "argocd",
                    "patch",
                    "application",
                    "fulfillops",
                    "--type",
                    "merge",
                    "-p",
                    '{"spec":{"syncPolicy":{"automated":{"selfHeal":false}}}}',
                )
                kube(
                    "-n",
                    NAMESPACE,
                    "scale",
                    "deployment/fulfillops-api",
                    "--replicas=3",
                )
                kube(
                    "-n",
                    "argocd",
                    "annotate",
                    "application",
                    "fulfillops",
                    "argocd.argoproj.io/refresh=hard",
                    "--overwrite",
                )
                wait_for(
                    lambda: (
                        obj("argocd", "application", "fulfillops")
                        .get("status", {})
                        .get("sync", {})
                        .get("status")
                        == "OutOfSync"
                    ),
                    "drift detection",
                )
                drift = obj("argocd", "application", "fulfillops")
                assert (
                    obj(NAMESPACE, "deployment", "fulfillops-api")["spec"]["replicas"]
                    == 3
                )
                save("application-drift.json", drift)
                record(
                    "Observed OutOfSync: API replicas manually three, Git specifies two; repair temporarily paused"
                )
            finally:
                kube("apply", "-f", str(ROOT / "infra/argocd/application.yaml"))
            assert (
                obj("argocd", "application", "fulfillops")["spec"]["syncPolicy"][
                    "automated"
                ]["selfHeal"]
                is True
            )
            wait_for(
                lambda: (
                    app_ready()
                    and obj(NAMESPACE, "deployment", "fulfillops-api")["spec"][
                        "replicas"
                    ]
                    == 2
                ),
                "automatic GitOps repair",
            )
            kube(
                "-n",
                NAMESPACE,
                "rollout",
                "status",
                "deployment/fulfillops-api",
                "--timeout=90s",
            )
            record(
                "Self-heal restored from committed Application: Synced/Healthy and two API replicas"
            )
            kube("-n", NAMESPACE, "delete", "pod", "postgres-0", "--wait=true")

            def replacement_ready():
                raw = kube(
                    "-n",
                    NAMESPACE,
                    "get",
                    "pod",
                    "postgres-0",
                    "--ignore-not-found",
                    "-o",
                    "json",
                    quiet=True,
                )
                if not raw.strip():
                    return False
                pod = json.loads(raw)
                statuses = pod.get("status", {}).get("containerStatuses", [])
                return (
                    pod["metadata"]["uid"] != pg_before
                    and bool(statuses)
                    and all(c.get("ready", False) for c in statuses)
                )

            wait_for(replacement_ready, "replacement database pod", 120)
            kube(
                "-n",
                NAMESPACE,
                "rollout",
                "status",
                "statefulset/postgres",
                "--timeout=90s",
            )
            wait_for(app_ready, "health after database recovery")
            after = snapshot(order_id)
            pvc_after = obj(NAMESPACE, "pvc", "postgres-data")
            assert before == after
            assert pvc_before["metadata"]["uid"] == pvc_after["metadata"]["uid"]
            assert pvc_before["spec"]["volumeName"] == pvc_after["spec"]["volumeName"]
            live_pods = json.loads(
                kube(
                    "-n",
                    NAMESPACE,
                    "get",
                    "pods",
                    "-l",
                    "app=fulfillops-api",
                    "-o",
                    "json",
                    quiet=True,
                )
            )["items"]
            live_url = stack.enter_context(forward(live_pods[0]["metadata"]["name"]))
            replay = httpx.post(
                live_url + "/api/v1/orders",
                json=payload,
                headers={"Idempotency-Key": key},
                timeout=10,
            )
            assert replay.status_code == 202 and replay.json() == {
                "order_id": order_id,
                "status": "queued",
            }
            save("database-after.json", after)
            save(
                "storage-proof.json",
                {
                    "before_pod_uid": pg_before,
                    "after_pod_uid": obj(NAMESPACE, "pod", "postgres-0")["metadata"][
                        "uid"
                    ],
                    "pvc_uid": pvc_after["metadata"]["uid"],
                    "volume": pvc_after["spec"]["volumeName"],
                },
            )
            save("application-after.json", obj("argocd", "application", "fulfillops"))
            kube(
                "-n", NAMESPACE, "get", "deployments,statefulset,pods,pvc", "-o", "wide"
            )
            kube("-n", NAMESPACE, "rollout", "history", "deployment/fulfillops-api")
            record(
                "PASS: Git sync, two APIs/two workers, drift repair and persistence after database pod replacement; "
                + (
                    "checker/races not rerun in repeat mode"
                    if args.repeat
                    else "fresh checker and cross-pod races passed"
                )
            )


if __name__ == "__main__":
    main()
