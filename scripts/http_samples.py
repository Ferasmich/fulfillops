"""Save observed client-side HTTP samples and a nearest-rank p95 summary."""

import argparse
import csv
import json
import math
import time
from datetime import UTC, datetime
from pathlib import Path

import httpx


def percentile(values, fraction=0.95):
    if not values or not 0 < fraction <= 1:
        raise ValueError("Nonempty samples and a fraction in (0, 1] are required")
    return sorted(values)[math.ceil(len(values) * fraction) - 1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--samples", type=int, default=250)
    parser.add_argument(
        "--output", type=Path, default=Path("evid/08-reliability/http-samples.csv")
    )
    args = parser.parse_args()
    if args.samples < 200 or not args.base_url.startswith(
        ("http://127.0.0.1:", "http://localhost:")
    ):
        parser.error("Use at least 200 samples against the isolated localhost endpoint")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    rows = []
    with httpx.Client(base_url=args.base_url, timeout=5) as client:
        for _ in range(args.samples):
            stamp = datetime.now(UTC).isoformat()
            start = time.perf_counter()
            try:
                status = client.get("/api/v1/catalog").status_code
            except httpx.TransportError:
                status = 0
            rows.append(
                {
                    "timestamp_utc": stamp,
                    "http_status": status,
                    "duration_seconds": time.perf_counter() - start,
                }
            )
    with args.output.open("w") as output:
        writer = csv.DictWriter(output, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    success = sum(200 <= row["http_status"] < 300 for row in rows)
    summary = {
        "route": "GET /api/v1/catalog",
        "samples": len(rows),
        "successes": success,
        "failures": len(rows) - success,
        "observed_success_percent": success / len(rows) * 100,
        "p95_seconds": percentile([row["duration_seconds"] for row in rows]),
        "p95_method": "nearest rank: sorted durations[ceil(0.95*n)-1]",
        "targets": {"success_percent": 99.5, "p95_seconds": 0.3},
        "environment": "Sequential local requests through kubectl tunnel, stable probe proxy and Kubernetes API Service; not a production SLO window",
    }
    summary["targets_met_in_this_window"] = (
        summary["observed_success_percent"] >= 99.5 and summary["p95_seconds"] < 0.3
    )
    args.output.with_suffix(".json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))
    return 0 if summary["targets_met_in_this_window"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
