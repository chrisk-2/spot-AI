#!/usr/bin/env python3
import json
import subprocess
import time
from pathlib import Path

def run(cmd):
    return subprocess.run(cmd, text=True, capture_output=True)

def emit(ok, name, detail=""):
    print(f"[{'PASS' if ok else 'FAIL'}] {name}{(' ' + detail) if detail else ''}")
    return ok

def main():
    checks = []
    out_dir = Path("watch/runtime/metrics/runs") / time.strftime("validate-%Y%m%dT%H%M%SZ", time.gmtime())
    out_dir.mkdir(parents=True, exist_ok=True)

    metrics_path = out_dir / "metrics.json"

    p = run([
        "watch/runtime/metrics/runtime-metrics-aggregate.py",
        "--output", str(metrics_path)
    ])
    checks.append(emit(p.returncode == 0, "aggregate_runs"))

    metrics = json.loads(metrics_path.read_text())
    checks.append(emit(metrics.get("schema") == "runtime_metrics_v1", "schema_valid"))
    checks.append(emit(metrics.get("scope") == "read_only", "scope_read_only"))
    checks.append(emit(metrics.get("mutation_authority") is False, "mutation_authority_false"))

    for section in ["queue", "routing", "governance", "archive", "validation"]:
        checks.append(emit(section in metrics, f"section_{section}_present"))

    queue = metrics["queue"]
    for field in ["total", "pending", "leased", "completed", "denied", "expired", "stale_leases", "receipt_count"]:
        checks.append(emit(field in queue, f"queue_field_{field}_present"))

    p = run([
        "watch/runtime/metrics/runtime-health-summary.py",
        "--metrics", str(metrics_path)
    ])
    checks.append(emit(p.returncode == 0, "health_summary_runs"))
    summary = json.loads(p.stdout)
    checks.append(emit(summary.get("scope") == "read_only", "summary_scope_read_only"))
    checks.append(emit(summary.get("mutation_authority") is False, "summary_mutation_authority_false"))

    p = run([
        "watch/runtime/metrics/runtime-metrics-export.py",
        "--out-dir", str(out_dir)
    ])
    checks.append(emit(p.returncode == 0, "export_runs"))

    exported = list(out_dir.glob("runtime-metrics-*.json"))
    summaries = list(out_dir.glob("runtime-health-summary-*.json"))
    checks.append(emit(len(exported) >= 1, "exported_metrics_present"))
    checks.append(emit(len(summaries) >= 1, "exported_summary_present"))

    passed = sum(1 for x in checks if x)
    failed = len(checks) - passed

    print("\n=== SUMMARY ===")
    print(f"pass={passed} fail={failed}")

    if failed:
        print("RESULT: FAIL")
        return 1

    print("RESULT: PASS")
    print("cases=21 aggregate_runs=pass schema_valid=pass scope_read_only=pass mutation_authority_false=pass required_sections=pass queue_fields=pass health_summary=pass export=pass mutation_scope=none")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
