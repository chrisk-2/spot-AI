#!/usr/bin/env python3
import json
import os
import time
import uuid
import fcntl
from datetime import datetime, timezone
from pathlib import Path

OUTCOME_PATH = Path(os.environ.get(
    "SPOT_ACTION_OUTCOMES",
    "/mnt/collective/logs/spot/actions/spot-action-outcomes.jsonl"
))
LOCAL_BUFFER = Path(os.environ.get(
    "SPOT_ACTION_OUTCOMES_BUFFER",
    "runtime/spot-action-outcomes.buffer.jsonl"
))

def now_iso():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

def _parse_ts(value):
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).timestamp()
    except Exception:
        return 0

def _append_line(path, line):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        f.write(line)
        f.flush()
        os.fsync(f.fileno())
        fcntl.flock(f, fcntl.LOCK_UN)

def append_record(record):
    record.setdefault("record_id", str(uuid.uuid4()))
    record.setdefault("created_at", now_iso())
    record.setdefault("schema", "spot-action-outcome.v1")

    line = json.dumps(record, sort_keys=True) + "\n"

    try:
        _append_line(OUTCOME_PATH, line)
        return {"ok": True, "path": str(OUTCOME_PATH), "buffered": False}
    except Exception as e:
        _append_line(LOCAL_BUFFER, line)
        return {"ok": True, "path": str(LOCAL_BUFFER), "buffered": True, "error": str(e)}

def make_decision_record(action_type, target, params, risk, decision, immediate_result=None, edited_delta=None):
    return {
        "record_type": "decision",
        "decision": {
            "action_type": action_type,
            "target": target,
            "params": params or {},
            "risk": risk,
            "decision": decision,
            "edited_delta": edited_delta
        },
        "immediate_result": immediate_result,
        "outcome": None
    }

def append_decision_record(action_type, target, params, risk, decision, immediate_result=None, edited_delta=None):
    return append_record(make_decision_record(
        action_type=action_type,
        target=target,
        params=params,
        risk=risk,
        decision=decision,
        immediate_result=immediate_result,
        edited_delta=edited_delta,
    ))

def make_outcome_update(parent_record_id, verdict, metric, before=None, after=None, notes=None):
    return {
        "record_type": "outcome_update",
        "parent_record_id": parent_record_id,
        "outcome": {
            "verdict": verdict,
            "metric": metric,
            "before": before,
            "after": after,
            "resolved_at": now_iso(),
            "notes": notes
        }
    }

def append_outcome_update(parent_record_id, verdict, metric, before=None, after=None, notes=None):
    return append_record(make_outcome_update(parent_record_id, verdict, metric, before, after, notes))

def iter_records(paths=None):
    paths = paths or [OUTCOME_PATH, LOCAL_BUFFER]
    for path in paths:
        if not path.exists():
            continue
        with path.open("r", encoding="utf-8") as f:
            for n, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                    rec["_source_path"] = str(path)
                    rec["_source_line"] = n
                    yield rec
                except Exception as e:
                    yield {"record_type": "invalid", "error": str(e), "_source_path": str(path), "_source_line": n}

def folded_records():
    decisions = {}
    updates = {}

    for rec in iter_records():
        if rec.get("record_type", "decision") == "outcome_update":
            parent = rec.get("parent_record_id")
            if parent:
                updates[parent] = rec.get("outcome")
            continue

        if "decision" in rec:
            rid = rec.get("record_id")
            if rid:
                decisions[rid] = rec

    for rid, outcome in updates.items():
        if rid in decisions:
            decisions[rid]["outcome"] = outcome

    return list(decisions.values())

def pending_records(min_age_seconds=180):
    cutoff = time.time() - int(min_age_seconds)
    for rec in folded_records():
        if rec.get("outcome") is not None:
            continue
        if _parse_ts(rec.get("created_at")) <= cutoff:
            yield rec

def summarize_outcomes(action_type=None, target=None, limit=20):
    rows = []
    for rec in folded_records():
        outcome = rec.get("outcome")
        decision = rec.get("decision", {})
        if not outcome:
            continue
        if action_type and action_type not in str(decision.get("action_type", "")):
            continue
        if target and target not in str(decision.get("target", "")):
            continue
        rows.append(rec)

    rows = rows[-int(limit):]
    if not rows:
        return ""

    buckets = {}
    for rec in rows:
        d = rec.get("decision", {})
        o = rec.get("outcome", {})
        key = (d.get("action_type", "unknown"), d.get("target", "unknown"), o.get("verdict", "unknown"))
        buckets[key] = buckets.get(key, 0) + 1

    lines = ["SPOT OUTCOME HISTORY DIGEST — resolved historical operator/action outcomes:"]
    for (atype, tgt, verdict), count in sorted(buckets.items()):
        lines.append(f"- {atype} on {tgt}: {count} {verdict}")
    lines.append("Use this as historical evidence only. It does not authorize execution.")
    return "\n".join(lines)
