#!/usr/bin/env python3
import argparse, hashlib, json, os
from pathlib import Path

ROOT = Path(os.environ.get("SPOT_ROLLBACK_ROOT", "/mnt/collective/logs/spot/rollbacks"))
INDEX = ROOT / "index.jsonl"
REQ = {"schema","rollback_id","correlation_id","target","plan","backup_path","rollback_defined","rollback_executed","payload_sha256","payload_stored_path","authority","execution_allowed","mutation_authority"}

def fail(m):
    print(f"[FAIL] {m}")
    raise SystemExit(1)

def shafile(p):
    h = hashlib.sha256()
    with p.open("rb") as f:
        for c in iter(lambda: f.read(1048576), b""):
            h.update(c)
    return h.hexdigest()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--correlation-id", default="")
    args = ap.parse_args()
    if not INDEX.exists():
        fail(f"missing index: {INDEX}")
    ids, corrs = set(), set()
    count = 0
    for n, line in enumerate(INDEX.read_text().splitlines(), 1):
        if not line.strip():
            continue
        count += 1
        rec = json.loads(line)
        miss = REQ - set(rec)
        if miss:
            fail(f"line {n} missing {sorted(miss)}")
        if rec["schema"] != "spot.rollback_receipt.v1":
            fail(f"line {n} bad schema")
        if rec["rollback_id"] in ids:
            fail(f"duplicate rollback_id {rec['rollback_id']}")
        ids.add(rec["rollback_id"])
        if rec["authority"] != "rollback_receipt_only":
            fail(f"line {n} bad authority")
        if rec["rollback_defined"] is not True or rec["rollback_executed"] is not False:
            fail(f"line {n} rollback invariant failed")
        if rec["execution_allowed"] is not False or rec["mutation_authority"] is not False:
            fail(f"line {n} authority expansion")
        p = Path(rec["payload_stored_path"])
        if not p.exists():
            fail(f"line {n} missing payload")
        if shafile(p) != rec["payload_sha256"]:
            fail(f"line {n} sha mismatch")
        corrs.add(rec["correlation_id"])
    if args.correlation_id and args.correlation_id not in corrs:
        fail(f"correlation_id not found: {args.correlation_id}")
    print(json.dumps({"ok": True, "entries": count, "correlations": len(corrs), "validated": True, "execution_allowed": False, "mutation_authority": False}, indent=2, sort_keys=True))
if __name__ == "__main__":
    main()
