#!/usr/bin/env python3
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path.cwd()

def utc_now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def load(path):
    return json.loads(Path(path).read_text())

def sha256_text(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def main():
    ap = argparse.ArgumentParser(description="Create dry-run Spot engineering transaction summary.")
    ap.add_argument("--patch-bundle", required=True)
    ap.add_argument("--review-json", required=True)
    ap.add_argument("--backup-binding", required=True)
    ap.add_argument("--rollback-binding", required=True)
    ap.add_argument("--journal", required=True)
    ap.add_argument("--validation-run", required=True)
    ap.add_argument("--out-dir", default="watch/apply/transactions")
    args = ap.parse_args()

    patch = load(args.patch_bundle)
    review = load(args.review_json)
    backup = load(args.backup_binding)
    rollback = load(args.rollback_binding)
    journal = load(args.journal)
    validation = load(args.validation_run)

    material = json.dumps({
        "patch_bundle_id": patch["patch_bundle_id"],
        "review_id": review["review_id"],
        "backup_binding_id": backup["backup_binding_id"],
        "rollback_binding_id": rollback["rollback_binding_id"],
        "apply_id": journal["apply_id"],
        "validation_run_id": validation["validation_run_id"]
    }, sort_keys=True)

    transaction_id = f"TX-{patch['request_id']}-{sha256_text(material)[:12]}"

    record = {
        "schema_version": "1.0",
        "created_utc": utc_now(),
        "transaction_id": transaction_id,
        "request_id": patch["request_id"],
        "patch_bundle_id": patch["patch_bundle_id"],
        "review_id": review["review_id"],
        "backup_binding_id": backup["backup_binding_id"],
        "rollback_binding_id": rollback["rollback_binding_id"],
        "apply_id": journal["apply_id"],
        "validation_run_id": validation["validation_run_id"],
        "execution_hash": journal["execution_hash"],
        "verdict": review["verdict"],
        "validation_passed": validation["passed"],
        "backup_verified": backup["verified"],
        "rollback_defined": bool(rollback["restore_strategy"]),
        "final_state": journal["state"],
        "mutation_performed": False,
        "execution_performed": False,
        "artifacts": {
            "patch_bundle": str(args.patch_bundle),
            "review_json": str(args.review_json),
            "backup_binding": str(args.backup_binding),
            "rollback_binding": str(args.rollback_binding),
            "journal": str(args.journal),
            "validation_run": str(args.validation_run)
        }
    }

    out_dir = ROOT / args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{transaction_id}.json"
    out.write_text(json.dumps(record, indent=2) + "\n")
    print(out)

if __name__ == "__main__":
    main()
