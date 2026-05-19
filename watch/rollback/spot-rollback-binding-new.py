#!/usr/bin/env python3
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path.cwd()

def utc_now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def sha256_text(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()

def main():
    ap = argparse.ArgumentParser(description="Create dry-run rollback binding manifest.")
    ap.add_argument("--patch-bundle", required=True)
    ap.add_argument("--backup-binding-id", required=True)
    ap.add_argument("--apply-id", required=True)
    ap.add_argument("--restore-strategy", default="restore-bound-backup")
    ap.add_argument("--validator", action="append", default=[])
    ap.add_argument("--out-dir", default="watch/rollback/bindings")
    args = ap.parse_args()

    patch = json.loads(Path(args.patch_bundle).read_text())

    material = json.dumps({
        "patch_bundle_id": patch["patch_bundle_id"],
        "backup_binding_id": args.backup_binding_id,
        "apply_id": args.apply_id,
        "restore_strategy": args.restore_strategy,
        "target": patch.get("target", {}),
        "files": patch.get("files", [])
    }, sort_keys=True)

    rollback_binding_id = f"RBIND-{patch['request_id']}-{sha256_text(material)[:12]}"

    record = {
        "schema_version": "1.0",
        "created_utc": utc_now(),
        "request_id": patch["request_id"],
        "patch_bundle_id": patch["patch_bundle_id"],
        "backup_binding_id": args.backup_binding_id,
        "apply_id": args.apply_id,
        "rollback_binding_id": rollback_binding_id,
        "restore_strategy": args.restore_strategy,
        "target": patch.get("target", {}),
        "target_files": patch.get("files", []),
        "validator_requirements": args.validator,
        "approval_required": patch.get("risk_class") == "high",
        "mutation_performed": False,
        "execution_performed": False
    }

    out_dir = ROOT / args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{rollback_binding_id}.json"
    out.write_text(json.dumps(record, indent=2) + "\n")
    print(out)

if __name__ == "__main__":
    main()
