#!/usr/bin/env python3
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path.cwd()

def utc_now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def sha256_text(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def main():
    ap = argparse.ArgumentParser(description="Create non-mutating Spot apply journal record.")
    ap.add_argument("--patch-bundle", required=True)
    ap.add_argument("--review-id", required=True)
    ap.add_argument("--backup-binding-id", required=True)
    ap.add_argument("--state", default="BLOCKED", choices=[
        "APPLIED",
        "BLOCKED",
        "FAILED_VALIDATION",
        "ROLLED_BACK",
        "HALTED_FOR_APPROVAL"
    ])
    ap.add_argument("--reason", default="dry-run journal record")
    ap.add_argument("--out-dir", default="watch/apply/journals")
    args = ap.parse_args()

    pb_path = Path(args.patch_bundle)
    patch = json.loads(pb_path.read_text())

    execution_material = json.dumps({
        "patch_bundle_id": patch["patch_bundle_id"],
        "review_id": args.review_id,
        "backup_binding_id": args.backup_binding_id,
        "state": args.state
    }, sort_keys=True)

    execution_hash = sha256_text(execution_material)
    apply_id = f"APPLY-{patch['request_id']}-{execution_hash[:12]}"

    record = {
        "schema_version": "1.0",
        "created_utc": utc_now(),
        "request_id": patch["request_id"],
        "patch_bundle_id": patch["patch_bundle_id"],
        "review_id": args.review_id,
        "backup_binding_id": args.backup_binding_id,
        "apply_id": apply_id,
        "execution_hash": execution_hash,
        "state": args.state,
        "reason": args.reason,
        "mutation_performed": False,
        "execution_performed": False
    }

    out_dir = ROOT / args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{apply_id}.json"
    out.write_text(json.dumps(record, indent=2) + "\n")
    print(out)

if __name__ == "__main__":
    main()
