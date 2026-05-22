#!/usr/bin/env python3
import argparse
import json
import os
from pathlib import Path

ROOT = Path(os.environ.get("SPOT_REMEDIATION_ROOT", "/mnt/collective/logs/spot/controlled-remediation"))
INDEX = ROOT / "rollback-index.jsonl"

REQ = {
    "schema",
    "rollback_id",
    "correlation_id",
    "validation_failed",
    "rollback_triggered",
    "rollback_verified",
    "pre_failure_sha256",
    "failed_sha256",
    "restored_sha256",
    "rollback_executed",
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
    ap = argparse.ArgumentParser(description="Validate rollback-on-failure proofs")
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
        if rec["schema"] != "spot.rollback_on_failure.v1":
            fail(f"line {n} bad schema")
        if rec["rollback_id"] in ids:
            fail(f"duplicate rollback_id {rec['rollback_id']}")
        ids.add(rec["rollback_id"])

        if not Path(rec["receipt_path"]).exists():
            fail(f"line {n} missing receipt")

        if rec["validation_failed"] is not True:
            fail(f"line {n} validation did not fail")
        if rec["rollback_triggered"] is not True:
            fail(f"line {n} rollback not triggered")
        if rec["rollback_verified"] is not True:
            fail(f"line {n} rollback not verified")
        if rec["rollback_executed"] is not True:
            fail(f"line {n} rollback not executed")
        if rec["pre_failure_sha256"] != rec["restored_sha256"]:
            fail(f"line {n} restored state mismatch")
        if rec["pre_failure_sha256"] == rec["failed_sha256"]:
            fail(f"line {n} failure did not change state")
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
        if rec["authority"] != "rollback_on_failure_only":
            fail(f"line {n} bad authority")

        corrs.add(rec["correlation_id"])

    if args.correlation_id and args.correlation_id not in corrs:
        fail(f"correlation_id not found: {args.correlation_id}")

    print(json.dumps({
        "ok": True,
        "entries": count,
        "correlations": len(corrs),
        "validated": True,
        "rollback_on_failure": True,
        "execution_allowed": False,
        "mutation_authority": False
    }, indent=2, sort_keys=True))

if __name__ == "__main__":
    main()
