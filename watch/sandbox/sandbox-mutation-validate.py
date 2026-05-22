#!/usr/bin/env python3
import argparse
import json
import os
from pathlib import Path

ROOT = Path(os.environ.get("SPOT_SANDBOX_ROOT", "/mnt/collective/logs/spot/sandbox-mutation"))
INDEX = ROOT / "index.jsonl"

REQ = {
    "schema",
    "mutation_id",
    "correlation_id",
    "sandbox_root",
    "workdir",
    "target_path",
    "backup_path",
    "rollback_path",
    "mutation_contained",
    "rollback_defined",
    "rollback_verified",
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
    ap = argparse.ArgumentParser(description="Validate sandbox mutation pilot records")
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
        if rec["schema"] != "spot.sandbox_mutation.v1":
            fail(f"line {n} bad schema")
        if rec["mutation_id"] in ids:
            fail(f"duplicate mutation_id {rec['mutation_id']}")
        ids.add(rec["mutation_id"])

        sandbox_root = Path(rec["sandbox_root"])
        target = Path(rec["target_path"])
        backup = Path(rec["backup_path"])
        rollback = Path(rec["rollback_path"])
        receipt = Path(rec["receipt_path"])

        for p in [target, backup, rollback, receipt]:
            if not p.exists():
                fail(f"line {n} missing path: {p}")

        if not str(target).startswith(str(sandbox_root)):
            fail(f"line {n} target escaped sandbox")
        if rec["mutation_contained"] is not True:
            fail(f"line {n} mutation not contained")
        if rec["rollback_defined"] is not True:
            fail(f"line {n} rollback not defined")
        if rec["rollback_verified"] is not True:
            fail(f"line {n} rollback not verified")
        if rec["production_path_touched"] is not False:
            fail(f"line {n} production path touched")
        if rec["service_restart_performed"] is not False:
            fail(f"line {n} service restart performed")
        if rec["worker_self_apply"] is not False:
            fail(f"line {n} worker self apply")
        if rec["spot_core_executor_only"] is not True:
            fail(f"line {n} executor invariant failed")
        if rec["execution_allowed"] is not False:
            fail(f"line {n} execution authority expansion")
        if rec["mutation_authority"] is not False:
            fail(f"line {n} mutation authority expansion")
        if rec["authority"] != "sandbox_mutation_only":
            fail(f"line {n} bad authority")

        corrs.add(rec["correlation_id"])

    if args.correlation_id and args.correlation_id not in corrs:
        fail(f"correlation_id not found: {args.correlation_id}")

    print(json.dumps({
        "ok": True,
        "entries": count,
        "correlations": len(corrs),
        "validated": True,
        "sandbox_only": True,
        "execution_allowed": False,
        "mutation_authority": False
    }, indent=2, sort_keys=True))

if __name__ == "__main__":
    main()
