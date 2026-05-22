#!/usr/bin/env python3
import argparse
import json
import os
from pathlib import Path

ROOT = Path(os.environ.get("SPOT_NOOP_EXEC_ROOT", "/mnt/collective/logs/spot/noop-executor"))
JOURNAL = ROOT / "index.jsonl"

REQ = {
    "schema",
    "noop_id",
    "correlation_id",
    "apply_attempt_id",
    "target",
    "action",
    "phase",
    "preflight_passed",
    "execution_performed",
    "mutation_performed",
    "rollback_required",
    "rollback_executed",
    "spot_core_executor_only",
    "worker_self_apply",
    "authority",
    "execution_allowed",
    "mutation_authority",
    "payload_stored_path"
}

def fail(msg):
    print(f"[FAIL] {msg}")
    raise SystemExit(1)

def main():
    ap = argparse.ArgumentParser(description="Validate Spot noop executor lifecycle records")
    ap.add_argument("--correlation-id", default="")
    args = ap.parse_args()

    if not JOURNAL.exists():
        fail(f"missing journal: {JOURNAL}")

    ids = set()
    apply_ids = set()
    corrs = set()
    count = 0

    for n, line in enumerate(JOURNAL.read_text().splitlines(), 1):
        if not line.strip():
            continue
        count += 1
        rec = json.loads(line)
        miss = REQ - set(rec)
        if miss:
            fail(f"line {n} missing {sorted(miss)}")
        if rec["schema"] != "spot.noop_executor.lifecycle.v1":
            fail(f"line {n} bad schema")
        if rec["noop_id"] in ids:
            fail(f"duplicate noop_id {rec['noop_id']}")
        ids.add(rec["noop_id"])
        if rec["apply_attempt_id"] in apply_ids:
            fail(f"duplicate apply_attempt_id {rec['apply_attempt_id']}")
        apply_ids.add(rec["apply_attempt_id"])
        if rec["phase"] != "noop":
            fail(f"line {n} phase not noop")
        if rec["preflight_passed"] is not True:
            fail(f"line {n} preflight not passed")
        if rec["execution_performed"] is not False:
            fail(f"line {n} execution performed")
        if rec["mutation_performed"] is not False:
            fail(f"line {n} mutation performed")
        if rec["rollback_executed"] is not False:
            fail(f"line {n} rollback executed")
        if rec["spot_core_executor_only"] is not True:
            fail(f"line {n} executor invariant failed")
        if rec["worker_self_apply"] is not False:
            fail(f"line {n} worker self apply")
        if rec["authority"] != "noop_executor_only":
            fail(f"line {n} bad authority")
        if rec["execution_allowed"] is not False:
            fail(f"line {n} execution authority expansion")
        if rec["mutation_authority"] is not False:
            fail(f"line {n} mutation authority expansion")
        if not Path(rec["payload_stored_path"]).exists():
            fail(f"line {n} missing payload")
        corrs.add(rec["correlation_id"])

    if args.correlation_id and args.correlation_id not in corrs:
        fail(f"correlation_id not found: {args.correlation_id}")

    print(json.dumps({
        "ok": True,
        "entries": count,
        "correlations": len(corrs),
        "validated": True,
        "execution_allowed": False,
        "mutation_authority": False
    }, indent=2, sort_keys=True))

if __name__ == "__main__":
    main()
