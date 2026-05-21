#!/usr/bin/env python3
import json
import statistics
from pathlib import Path
from datetime import datetime, timezone

ROOTS = [
    Path("/mnt/collective/logs/spot/reviews"),
    Path("/mnt/collective/logs/spot/runtime"),
    Path("watch/state"),
    Path("watch/apply/journals"),
]

def load_rows(path):
    try:
        if path.suffix == ".json":
            return [json.loads(path.read_text(errors="replace"))]
        if path.suffix == ".jsonl":
            out = []
            for line in path.read_text(errors="replace").splitlines():
                if line.strip():
                    out.append(json.loads(line))
            return out
    except Exception:
        return []
    return []

def all_records():
    out = []
    for root in ROOTS:
        if not root.exists():
            continue
        for f in root.rglob("*"):
            if f.is_file() and f.suffix in {".json", ".jsonl"}:
                for row in load_rows(f):
                    if isinstance(row, dict):
                        row["_source_file"] = str(f)
                        out.append(row)
    return out

def signal(row, terms):
    text = json.dumps(row, sort_keys=True, default=str).lower()
    return any(x in text for x in terms)

def latency(row):
    for key in [
        "latency_ms",
        "duration_ms",
        "review_latency_ms",
        "elapsed_ms",
        "runtime_ms",
        "queue_latency_ms",
        "total_ms",
    ]:
        if key in row:
            try:
                return float(row[key])
            except Exception:
                pass
    return None

def summarize(values):
    values = sorted(values)
    if not values:
        return {
            "count": 0,
            "min_ms": None,
            "max_ms": None,
            "avg_ms": None,
            "p50_ms": None,
            "p95_ms": None,
        }

    p95_index = min(len(values) - 1, int(round((len(values) - 1) * 0.95)))

    return {
        "count": len(values),
        "min_ms": round(values[0], 3),
        "max_ms": round(values[-1], 3),
        "avg_ms": round(statistics.mean(values), 3),
        "p50_ms": round(statistics.median(values), 3),
        "p95_ms": round(values[p95_index], 3),
    }

records = all_records()

reviews = [
    r for r in records
    if signal(r, ["review", "worker-05", "verdict", "review_type"])
]

leases = [
    r for r in records
    if signal(r, ["lease", "lease_id", "lease_owner", "lease_ttl", "owner"])
]

latencies = [latency(r) for r in reviews]
latencies = [x for x in latencies if x is not None]

verdicts = {}
for r in reviews:
    v = str(r.get("verdict") or r.get("decision") or "unknown").upper()
    verdicts[v] = verdicts.get(v, 0) + 1

owners = {}
for r in leases:
    owner = str(
        r.get("lease_owner")
        or r.get("owner")
        or r.get("worker")
        or "unknown"
    )
    owners[owner] = owners.get(owner, 0) + 1

out = {
    "ts": datetime.now(timezone.utc).isoformat(),
    "mode": "read_only",
    "mutation_authority": False,
    "executor": "spot-core",
    "records_scanned": len(records),
    "review": {
        "records": len(reviews),
        "verdicts": verdicts,
        "latency": summarize(latencies),
    },
    "lease": {
        "records": len(leases),
        "owners": owners,
    },
}

print(json.dumps(out, indent=2, sort_keys=True))
