#!/usr/bin/env python3
import argparse
import json
import os
from pathlib import Path

ROOT = Path(os.environ.get("SPOT_REMEDIATION_ROOT", "/mnt/collective/logs/spot/controlled-remediation"))
INDEX = ROOT / "index.jsonl"

REQ = {
    "schema",
    "remediation_id",
    "correlation_id",
    "workdir",
    "target_path",
    "backup_path",
    "rollback_path",
    "backup_sha256",
    "mutated_sha256",
    "rollback_sha256",
    "rollback_defined",
    "rollback_verified",
    "rollback_executed",
    "mutation_contained",
    "production_path_touched",
    "service_restart_performed",
    "worker_self_apply",
    "spot_core_executor_only",
    "execution_allowed",
    "mutation_authority",
    "authority",
    "receipt_path"
}

def fail(msg):
    print(f"[FAIL] {msg}")
    raise SystemExit(1)

def main():
    ap = argparse.ArgumentParser(description="Validate controlled remediation records")
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
        if rec["schema"] != "spot.controlled_remediation.v1":
            fail(f"line {n} bad schema")
        if rec["remediation_id"] in ids:
            fail(f"duplicate remediation_id {rec['remediation_id']}")
        ids.add(rec["remediation_id"])

        for key in ["target_path", "backup_path", "rollback_path", "receipt_path"]:
            if not Path(rec[key]).exists():
                fail(f"line {n} missing {key}: {rec[key]}")

        if rec["rollback_defined"] is not True:
            fail(f"line {n} rollback not defined")
        if rec["rollback_verified"] is not True:
            fail(f"line {n} rollback not verified")
        if rec["rollback_executed"] is not False:
            fail(f"line {n} rollback unexpectedly executed")
        if rec["mutation_contained"] is not True:
            fail(f"line {n} mutation not contained")
        if rec["production_path_touched"] is not False:
            fail(f"line {n} production path touched")
        if rec["service_restart_performed"] is not False:
            fail(f"line {n} service restarted")
        if rec["worker_self_apply"] is not False:
            fail(f"line {n} worker self apply")
        if rec["spot_core_executor_only"] is not True:
            fail(f"line {n} executor invariant failed")
        if rec["execution_allowed"] is not False:
            fail(f"line {n} execution authority expansion")
        if rec["mutation_authority"] is not False:
            fail(f"line {n} mutation authority expansion")
        if rec["authority"] != "controlled_remediation_only":
            fail(f"line {n} bad authority")

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
