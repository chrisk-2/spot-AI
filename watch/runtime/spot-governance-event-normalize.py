#!/usr/bin/env python3
import argparse
import hashlib
import json
import sys
from pathlib import Path
from datetime import datetime, timezone

ROOTS = [
    Path("/mnt/collective/logs/spot/reviews"),
    Path("/mnt/collective/logs/spot/runtime"),
    Path("watch/state"),
    Path("watch/apply/journals"),
]

EVENT_TERMS = {
    "review": ["review", "worker-05", "verdict", "review_type"],
    "queue": ["queue", "queued", "dequeue", "queue_id"],
    "lease": ["lease", "lease_id", "lease_owner", "lease_ttl"],
    "routing": ["routing", "route", "primary_role", "fallback"],
    "backup": ["backup", "backup_path", "backup_id"],
    "rollback": ["rollback", "rollback_id"],
    "validation": ["validate", "validation", "spot validate"],
    "journal": ["journal", "jsonl", "corrupt"],
    "runtime": ["runtime", "telemetry", "health"],
    "governance": ["governance", "policy", "authority", "allowed"],
}

def now():
    return datetime.now(timezone.utc).isoformat()

def stable_id(source_file, line_no, row):
    raw = json.dumps(row, sort_keys=True, default=str)
    h = hashlib.sha256(f"{source_file}:{line_no}:{raw}".encode("utf-8")).hexdigest()
    return "gev_" + h[:24]

def load_rows(path):
    out = []
    try:
        if path.suffix == ".json":
            obj = json.loads(path.read_text(errors="replace"))
            if isinstance(obj, dict):
                out.append((None, obj))
        elif path.suffix == ".jsonl":
            for n, line in enumerate(path.read_text(errors="replace").splitlines(), 1):
                if not line.strip():
                    continue
                try:
                    obj = json.loads(line)
                    if isinstance(obj, dict):
                        out.append((n, obj))
                except Exception:
                    continue
    except Exception:
        return []
    return out

def classify(row):
    text = json.dumps(row, sort_keys=True, default=str).lower()
    scores = {}
    for event_type, terms in EVENT_TERMS.items():
        scores[event_type] = sum(1 for term in terms if term in text)
    event_type, score = max(scores.items(), key=lambda x: x[1])
    return event_type if score > 0 else "runtime"

def first(row, keys):
    for key in keys:
        if key in row and row[key] not in ("", None):
            return row[key]
    return None

def normalize(row, source_file, line_no):
    event_type = classify(row)

    worker = first(row, ["worker", "chosen_worker", "lease_owner", "target_worker"])
    request_id = first(row, ["request_id", "req_id", "id"])
    queue_id = first(row, ["queue_id"])
    lease_id = first(row, ["lease_id"])
    review_id = first(row, ["review_id"])
    backup_id = first(row, ["backup_id"])
    rollback_id = first(row, ["rollback_id"])
    replay_id = first(row, ["replay_id"])

    verdict = first(row, ["verdict", "decision", "result"])
    allowed = first(row, ["allowed", "execution_allowed"])
    if isinstance(allowed, str):
        allowed = allowed.lower() in ("true", "yes", "1", "pass", "allowed")

    event = {
        "schema_version": "spot.governance.event.v1",
        "event_id": stable_id(source_file, line_no, row),
        "ts": str(first(row, ["ts", "timestamp", "created_at"]) or now()),
        "event_type": event_type,
        "authority": {
            "executor": "spot-core",
            "mutation_authority": False,
            "worker_self_apply_allowed": False,
        },
        "source": {
            "component": str(first(row, ["component", "provider", "source"]) or event_type),
            "worker": str(worker) if worker is not None else None,
            "file": source_file,
        },
        "correlation": {
            "request_id": str(request_id) if request_id is not None else None,
            "queue_id": str(queue_id) if queue_id is not None else None,
            "lease_id": str(lease_id) if lease_id is not None else None,
            "review_id": str(review_id) if review_id is not None else None,
            "backup_id": str(backup_id) if backup_id is not None else None,
            "rollback_id": str(rollback_id) if rollback_id is not None else None,
            "replay_id": str(replay_id) if replay_id is not None else None,
        },
        "subject": {
            "target": str(first(row, ["target", "host", "node"])) if first(row, ["target", "host", "node"]) is not None else None,
            "service": str(first(row, ["service"])) if first(row, ["service"]) is not None else None,
            "role": str(first(row, ["role", "primary_role"])) if first(row, ["role", "primary_role"]) is not None else None,
            "risk_class": str(first(row, ["risk_class", "risk"])) if first(row, ["risk_class", "risk"]) is not None else None,
        },
        "decision": {
            "verdict": str(verdict) if verdict is not None else None,
            "allowed": allowed if isinstance(allowed, bool) else None,
            "blocked_reason": str(first(row, ["blocked_reason", "reason"])) if first(row, ["blocked_reason", "reason"]) is not None else None,
            "policy_gate": str(first(row, ["policy_gate", "gate"])) if first(row, ["policy_gate", "gate"]) is not None else None,
        },
        "metrics": {
            k: row[k]
            for k in row
            if k.endswith("_ms") or k.endswith("_count") or k in ("latency_ms", "duration_ms", "queue_depth")
        },
        "raw_ref": {
            "source_file": source_file,
            "line": line_no,
        },
        "integrity": {
            "normalized_from_raw": True,
            "read_only": True,
            "notes": "normalization does not authorize execution",
        },
    }
    return event

def iter_events(limit):
    count = 0
    for root in ROOTS:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            s = str(path)
            if "/corrupt/" in s:
                continue
            if not path.is_file() or path.suffix not in {".json", ".jsonl"}:
                continue
            for line_no, row in load_rows(path):
                yield normalize(row, str(path), line_no)
                count += 1
                if limit and count >= limit:
                    return

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=100)
    ap.add_argument("--summary", action="store_true")
    args = ap.parse_args()

    events = list(iter_events(args.limit))

    if args.summary:
        by_type = {}
        for e in events:
            by_type[e["event_type"]] = by_type.get(e["event_type"], 0) + 1
        print(json.dumps({
            "schema_version": "spot.governance.event.summary.v1",
            "ts": now(),
            "mode": "read_only",
            "mutation_authority": False,
            "executor": "spot-core",
            "count": len(events),
            "by_type": by_type,
        }, indent=2, sort_keys=True))
        return 0

    for e in events:
        print(json.dumps(e, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
