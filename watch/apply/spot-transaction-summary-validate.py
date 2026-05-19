#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path

REQUIRED = [
    "schema_version",
    "created_utc",
    "transaction_id",
    "request_id",
    "patch_bundle_id",
    "review_id",
    "backup_binding_id",
    "rollback_binding_id",
    "apply_id",
    "validation_run_id",
    "execution_hash",
    "verdict",
    "validation_passed",
    "backup_verified",
    "rollback_defined",
    "final_state",
    "mutation_performed",
    "execution_performed",
    "artifacts"
]

def fail(msg):
    print(f"[FAIL] {msg}", file=sys.stderr)
    raise SystemExit(1)

def main():
    ap = argparse.ArgumentParser(description="Validate Spot transaction summary.")
    ap.add_argument("transaction")
    args = ap.parse_args()

    data = json.loads(Path(args.transaction).read_text())

    for k in REQUIRED:
        if k not in data:
            fail(f"missing field: {k}")

    if data["mutation_performed"] is not False:
        fail("mutation_performed must be false")

    if data["execution_performed"] is not False:
        fail("execution_performed must be false")

    if data["verdict"] != "PASS":
        fail("transaction verdict must be PASS for smoke")

    if data["validation_passed"] is not True:
        fail("validation_passed must be true")

    if data["backup_verified"] is not True:
        fail("backup_verified must be true")

    if data["rollback_defined"] is not True:
        fail("rollback_defined must be true")

    if data["final_state"] not in ["BLOCKED", "HALTED_FOR_APPROVAL"]:
        fail("dry-run transaction final_state must remain non-mutating")

    print(f"[PASS] transaction summary valid: {args.transaction}")

if __name__ == "__main__":
    main()
