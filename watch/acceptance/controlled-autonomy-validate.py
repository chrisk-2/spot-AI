#!/usr/bin/env python3
import argparse
import json
import os
from pathlib import Path

ROOT = Path(os.environ.get("SPOT_ACCEPTANCE_ROOT", "/mnt/collective/logs/spot/acceptance"))
INDEX = ROOT / "index.jsonl"

REQ = {
    "schema",
    "acceptance_id",
    "correlation_id",
    "counts",
    "decision",
    "controlled_autonomy_ready",
    "live_production_mutation_authorized",
    "proposal_only_learning",
    "spot_core_executor_only",
    "worker_self_apply",
    "execution_allowed",
    "mutation_authority",
    "authority",
    "receipt_path"
}

def fail(msg):
    print(f"[FAIL] {msg}")
    raise SystemExit(1)

def main():
    ap = argparse.ArgumentParser(description="Validate controlled autonomy acceptance records")
    ap.add_argument("--correlation-id", default="")
    args = ap.parse_args()

    if not INDEX.exists():
        fail(f"missing index: {INDEX}")

    ids = set()
    corrs = set()
    count = 0

    for n, line in enumerate(INDEX.read_text().splitlines(), 1):
        if not line.strip():
            continue
        count += 1
        rec = json.loads(line)

        miss = REQ - set(rec)
        if miss:
            fail(f"line {n} missing {sorted(miss)}")
        if rec["schema"] != "spot.controlled_autonomy_acceptance.v1":
            fail(f"line {n} bad schema")
        if rec["acceptance_id"] in ids:
            fail(f"duplicate acceptance_id {rec['acceptance_id']}")
        ids.add(rec["acceptance_id"])

        if rec["decision"] != "PASS":
            fail(f"line {n} decision not PASS")
        if rec["controlled_autonomy_ready"] is not True:
            fail(f"line {n} not ready")
        if rec["live_production_mutation_authorized"] is not False:
            fail(f"line {n} production mutation authorized")
        if rec["proposal_only_learning"] is not True:
            fail(f"line {n} learning not proposal-only")
        if rec["spot_core_executor_only"] is not True:
            fail(f"line {n} executor invariant failed")
        if rec["worker_self_apply"] is not False:
            fail(f"line {n} worker self apply")
        if rec["execution_allowed"] is not False:
            fail(f"line {n} execution authority expansion")
        if rec["mutation_authority"] is not False:
            fail(f"line {n} mutation authority expansion")
        if rec["authority"] != "acceptance_gate_only":
            fail(f"line {n} bad authority")
        if not Path(rec["receipt_path"]).exists():
            fail(f"line {n} missing receipt")

        corrs.add(rec["correlation_id"])

    if args.correlation_id and args.correlation_id not in corrs:
        fail(f"correlation_id not found: {args.correlation_id}")

    print(json.dumps({
        "ok": True,
        "entries": count,
        "correlations": len(corrs),
        "validated": True,
        "controlled_autonomy_ready": True,
        "live_production_mutation_authorized": False,
        "execution_allowed": False,
        "mutation_authority": False
    }, indent=2, sort_keys=True))

if __name__ == "__main__":
    main()
