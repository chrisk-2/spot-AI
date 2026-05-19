#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path

REQUIRED = [
    "schema_version",
    "created_utc",
    "request_id",
    "patch_bundle_id",
    "backup_binding_id",
    "backup_manifest_id",
    "backup_path",
    "target",
    "target_files",
    "verified",
    "dry_run",
    "mutation_performed",
    "execution_performed"
]

def fail(msg):
    print(f"[FAIL] {msg}", file=sys.stderr)
    raise SystemExit(1)

def main():
    ap = argparse.ArgumentParser(description="Validate dry-run backup binding manifest.")
    ap.add_argument("binding")
    args = ap.parse_args()

    data = json.loads(Path(args.binding).read_text())

    for k in REQUIRED:
        if k not in data:
            fail(f"missing field: {k}")

    if not data["backup_binding_id"]:
        fail("backup_binding_id missing")

    if not data["backup_manifest_id"]:
        fail("backup_manifest_id missing")

    if not data["backup_path"]:
        fail("backup_path missing")

    if data["verified"] is not True:
        fail("backup binding must be verified")

    if data["dry_run"] is not True:
        fail("Phase 3.6 backup binding must be dry_run=true")

    if data["mutation_performed"] is not False:
        fail("mutation_performed must be false")

    if data["execution_performed"] is not False:
        fail("execution_performed must be false")

    print(f"[PASS] backup binding valid: {args.binding}")

if __name__ == "__main__":
    main()
