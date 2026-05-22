#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
from pathlib import Path

ROOT = Path(os.environ.get("SPOT_FAILURE_ROOT", "/mnt/collective/logs/spot/failure-proofs"))
INDEX = ROOT / "index.jsonl"

REQ = {
    "schema",
    "proof_id",
    "correlation_id",
    "failure_type",
    "expected_result",
    "evidence",
    "safe_failure",
    "rollback_required",
    "rollback_executed",
    "payload_sha256",
    "payload_stored_path",
    "execution_allowed",
    "mutation_authority",
    "authority"
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
    ap = argparse.ArgumentParser(description="Validate Spot failure/crash proofs")
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

        if rec["schema"] != "spot.failure_proof.v1":
            fail(f"line {n} bad schema")

        if rec["proof_id"] in ids:
            fail(f"duplicate proof_id {rec['proof_id']}")

        ids.add(rec["proof_id"])

        if rec["authority"] != "failure_proof_only":
            fail(f"line {n} bad authority")

        if rec["safe_failure"] is not True:
            fail(f"line {n} unsafe failure")

        if rec["rollback_executed"] is not False:
            fail(f"line {n} rollback executed")

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
