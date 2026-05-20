#!/usr/bin/env python3
import argparse
import json
import subprocess
from pathlib import Path

def load_metrics(path):
    return json.loads(Path(path).read_text())

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--metrics")
    args = ap.parse_args()

    if args.metrics:
        metrics = load_metrics(args.metrics)
    else:
        p = subprocess.run(
            ["watch/runtime/metrics/runtime-metrics-aggregate.py"],
            text=True,
            capture_output=True,
            check=True
        )
        metrics = json.loads(p.stdout)

    queue = metrics["queue"]
    routing = metrics["routing"]

    status = "ok"
    findings = []

    if queue["stale_leases"] > 0:
        status = "warn"
        findings.append(f"stale_leases={queue['stale_leases']}")

    if routing["malformed_lines"] > 0:
        status = "warn"
        findings.append(f"routing_malformed_lines={routing['malformed_lines']}")

    if routing["violation_count"] > 0:
        status = "warn"
        findings.append(f"routing_violations={routing['violation_count']}")

    summary = {
        "schema": "runtime_health_summary_v1",
        "scope": "read_only",
        "mutation_authority": False,
        "status": status,
        "findings": findings,
        "queue_total": queue["total"],
        "queue_pending": queue["pending"],
        "queue_leased": queue["leased"],
        "queue_completed": queue["completed"],
        "queue_receipts": queue["receipt_count"],
        "routing_audit_lines": routing["lines"],
        "routing_fallback_count": routing["fallback_count"]
    }

    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
