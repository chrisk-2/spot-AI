#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
from pathlib import Path

ROOT = Path(os.environ.get("SPOT_APPROVAL_ROOT", "/mnt/collective/logs/spot/approvals"))
INDEX = ROOT / "index.jsonl"

REQ = {
    "schema",
    "approval_id",
    "correlation_id",
    "risk_class",
    "decision",
    "reason",
    "operator",
    "payload_sha256",
    "payload_stored_path",
    "authority",
    "spot_core_executor_only",
    "worker_self_apply",
    "execution_allowed",
    "mutation_authority"
}

def fail(msg):
    print(f"[FAIL] {msg}")
    raise SystemExit(1)

def sha_file(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for c in iter(lambda: f.read(1048576), b""):
            h.update(c)
    return h.hexdigest()

def main():
    ap = argparse.ArgumentParser(description="Validate Spot approval escalation records")
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

        if rec["schema"] != "spot.approval_escalation.v1":
            fail(f"line {n} bad schema")

        if rec["approval_id"] in ids:
            fail(f"duplicate approval_id {rec['approval_id']}")

        ids.add(rec["approval_id"])

        if rec["authority"] != "approval_record_only":
            fail(f"line {n} bad authority")

        if rec["spot_core_executor_only"] is not True:
            fail(f"line {n} executor invariant failed")

        if rec["worker_self_apply"] is not False:
            fail(f"line {n} worker self apply invariant failed")

        if rec["execution_allowed"] is not False:
            fail(f"line {n} execution authority expansion")

        if rec["mutation_authority"] is not False:
            fail(f"line {n} mutation authority expansion")

        p = Path(rec["payload_stored_path"])

        if not p.exists():
            fail(f"line {n} missing payload")

        if sha_file(p) != rec["payload_sha256"]:
            fail(f"line {n} sha mismatch")

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
