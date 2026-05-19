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
    "apply_id",
    "rollback_binding_id",
    "restore_strategy",
    "target",
    "target_files",
    "validator_requirements",
    "approval_required",
    "mutation_performed",
    "execution_performed"
]

def fail(msg):
    print(f"[FAIL] {msg}", file=sys.stderr)
    raise SystemExit(1)

def main():
    ap = argparse.ArgumentParser(description="Validate rollback binding manifest.")
    ap.add_argument("binding")
    args = ap.parse_args()

    data = json.loads(Path(args.binding).read_text())

    for k in REQUIRED:
        if k not in data:
            fail(f"missing field: {k}")

    if not data["backup_binding_id"]:
        fail("backup_binding_id missing")

    if not data["apply_id"]:
        fail("apply_id missing")

    if not data["restore_strategy"]:
        fail("restore_strategy missing")

    if not isinstance(data["target_files"], list):
        fail("target_files must be list")

    if not isinstance(data["validator_requirements"], list):
        fail("validator_requirements must be list")

    if data["mutation_performed"] is not False:
        fail("mutation_performed must be false for Phase 3.5")

    if data["execution_performed"] is not False:
        fail("execution_performed must be false for Phase 3.5")

    print(f"[PASS] rollback binding valid: {args.binding}")

if __name__ == "__main__":
    main()
