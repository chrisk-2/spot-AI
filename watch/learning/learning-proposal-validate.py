#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
from pathlib import Path

ROOT = Path(os.environ.get("SPOT_LEARNING_ROOT", "/mnt/collective/logs/spot/learning"))
INDEX = ROOT / "index.jsonl"

REQ = {
    "schema",
    "learning_id",
    "correlation_id",
    "lesson",
    "recommendation",
    "proposal_only",
    "requires_review",
    "auto_apply",
    "execution_allowed",
    "mutation_authority",
    "authority",
    "payload_sha256",
    "payload_stored_path"
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
    ap = argparse.ArgumentParser(description="Validate proposal-only learning records")
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
        if rec["schema"] != "spot.learning_proposal.v1":
            fail(f"line {n} bad schema")
        if rec["learning_id"] in ids:
            fail(f"duplicate learning_id {rec['learning_id']}")
        ids.add(rec["learning_id"])

        if rec["proposal_only"] is not True:
            fail(f"line {n} not proposal-only")
        if rec["requires_review"] is not True:
            fail(f"line {n} review not required")
        if rec["auto_apply"] is not False:
            fail(f"line {n} auto_apply enabled")
        if rec["execution_allowed"] is not False:
            fail(f"line {n} execution authority expansion")
        if rec["mutation_authority"] is not False:
            fail(f"line {n} mutation authority expansion")
        if rec["authority"] != "learning_proposal_only":
            fail(f"line {n} bad authority")

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
        "proposal_only": True,
        "execution_allowed": False,
        "mutation_authority": False
    }, indent=2, sort_keys=True))

if __name__ == "__main__":
    main()
