#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
from pathlib import Path

ROOT = Path(os.environ.get("SPOT_GOVERNANCE_BUNDLE_ROOT", "/mnt/collective/logs/spot/governance-bundles"))
INDEX = ROOT / "index.jsonl"

REQ = {"schema","bundle_id","ts","correlation_id","manifest_sha256","manifest_stored_path","counts","authority","execution_allowed","mutation_authority","replay_audit_ready"}

def fail(msg):
    print(f"[FAIL] {msg}")
    raise SystemExit(1)

def shafile(path):
    return hashlib.sha256(path.read_text(encoding="utf-8").encode("utf-8")).hexdigest()

def main():
    ap = argparse.ArgumentParser(description="Validate governance bundles")
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
        if rec["schema"] != "spot.governance_bundle.index.v1":
            fail(f"line {n} bad schema")
        if rec["bundle_id"] in ids:
            fail(f"duplicate bundle_id {rec['bundle_id']}")
        ids.add(rec["bundle_id"])
        if rec["authority"] != "governance_bundle_only":
            fail(f"line {n} bad authority")
        if rec["execution_allowed"] is not False:
            fail(f"line {n} execution authority expansion")
        if rec["mutation_authority"] is not False:
            fail(f"line {n} mutation authority expansion")
        if rec["replay_audit_ready"] is not True:
            fail(f"line {n} replay audit not ready")
        p = Path(rec["manifest_stored_path"])
        if not p.exists():
            fail(f"line {n} missing manifest")
        if shafile(p) != rec["manifest_sha256"]:
            fail(f"line {n} manifest sha mismatch")
        manifest = json.loads(p.read_text(encoding="utf-8"))
        for sec, rows in manifest.get("sections", {}).items():
            for item in rows:
                if item.get("execution_allowed") is not False:
                    fail(f"manifest {rec['bundle_id']} section {sec} expands execution authority")
                if item.get("mutation_authority") is not False:
                    fail(f"manifest {rec['bundle_id']} section {sec} expands mutation authority")
        corrs.add(rec["correlation_id"])

    if args.correlation_id and args.correlation_id not in corrs:
        fail(f"correlation_id not found: {args.correlation_id}")

    print(json.dumps({
        "ok": True,
        "entries": count,
        "correlations": len(corrs),
        "validated": True,
        "execution_allowed": False,
        "mutation_authority": False,
        "replay_audit_ready": True
    }, indent=2, sort_keys=True))

if __name__ == "__main__":
    main()
