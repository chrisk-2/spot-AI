#!/usr/bin/env python3
import argparse
import json
import time
from pathlib import Path

QUEUE_RUNS = Path("watch/runtime/queue/runs")
ROUTING_AUDIT = Path("watch/state/routing-audit.jsonl")
SPOT_LOG_ROOT = Path("/mnt/collective/logs/spot")

def now_iso():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

def safe_load_json(path):
    try:
        return json.loads(Path(path).read_text())
    except Exception as e:
        return {"_error": str(e), "_path": str(path)}

def count_queue_runs(queue_runs):
    result = {
        "total": 0,
        "pending": 0,
        "leased": 0,
        "completed": 0,
        "denied": 0,
        "expired": 0,
        "stale_leases": 0,
        "receipt_count": 0,
        "runs": 0,
        "malformed_runs": 0
    }

    now = int(time.time())

    if not queue_runs.exists():
        return result

    for state_path in queue_runs.glob("*/queue-state.json"):
        result["runs"] += 1
        state = safe_load_json(state_path)
        if "_error" in state:
            result["malformed_runs"] += 1
            continue

        for candidate in state.get("candidates", {}).values():
            result["total"] += 1
            s = candidate.get("state", "unknown")
            if s in result:
                result[s] += 1

            lease = candidate.get("lease") or {}
            if s == "leased" and lease.get("expires_ts", 0) <= now:
                result["stale_leases"] += 1

            result["receipt_count"] += len(candidate.get("receipts", []))

    return result

def count_routing_audit(path):
    result = {
        "exists": path.exists(),
        "lines": 0,
        "malformed_lines": 0,
        "fallback_count": 0,
        "violation_count": 0
    }

    if not path.exists():
        return result

    for line in path.read_text(errors="replace").splitlines():
        if not line.strip():
            continue
        result["lines"] += 1
        try:
            obj = json.loads(line)
        except Exception:
            result["malformed_lines"] += 1
            continue

        route_type = str(obj.get("route_type", "")).lower()
        decision = str(obj.get("decision", "")).lower()
        if "fallback" in route_type or "fallback" in decision:
            result["fallback_count"] += 1
        if obj.get("violation") or "violation" in decision:
            result["violation_count"] += 1

    return result

def count_spot_logs(root):
    result = {
        "root_exists": root.exists(),
        "review_logs": 0,
        "action_logs": 0,
        "backup_logs": 0,
        "rollback_logs": 0,
        "learning_logs": 0,
        "archive_logs": 0
    }

    if not root.exists():
        return result

    mapping = {
        "reviews": "review_logs",
        "actions": "action_logs",
        "backups": "backup_logs",
        "rollbacks": "rollback_logs",
        "learning": "learning_logs",
        "archive": "archive_logs"
    }

    for dirname, field in mapping.items():
        d = root / dirname
        if d.exists():
            result[field] = sum(1 for p in d.rglob("*") if p.is_file())

    return result

def build_metrics(args):
    queue = count_queue_runs(Path(args.queue_runs))
    routing = count_routing_audit(Path(args.routing_audit))
    logs = count_spot_logs(Path(args.log_root))

    metrics = {
        "schema": "runtime_metrics_v1",
        "generated_at": now_iso(),
        "scope": "read_only",
        "mutation_authority": False,
        "queue": queue,
        "routing": routing,
        "governance": {
            "deny_count": logs["action_logs"],
            "review_log_count": logs["review_logs"],
            "log_root_exists": logs["root_exists"]
        },
        "archive": {
            "archive_log_count": logs["archive_logs"]
        },
        "validation": {
            "latest_known_result": "external",
            "integrated_validator": False
        },
        "raw_log_counts": logs
    }

    return metrics

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--queue-runs", default=str(QUEUE_RUNS))
    ap.add_argument("--routing-audit", default=str(ROUTING_AUDIT))
    ap.add_argument("--log-root", default=str(SPOT_LOG_ROOT))
    ap.add_argument("--output")
    args = ap.parse_args()

    metrics = build_metrics(args)

    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        tmp = out.with_suffix(out.suffix + ".tmp")
        tmp.write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n")
        tmp.replace(out)

    print(json.dumps(metrics, indent=2, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
