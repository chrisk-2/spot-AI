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
    "review_id",
    "backup_binding_id",
    "apply_id",
    "execution_hash",
    "state",
    "mutation_performed",
    "execution_performed"
]

def fail(msg):
    print(f"[FAIL] {msg}", file=sys.stderr)
    raise SystemExit(1)

def main():
    ap = argparse.ArgumentParser(description="Validate Spot apply journal record.")
    ap.add_argument("journal")
    args = ap.parse_args()

    data = json.loads(Path(args.journal).read_text())

    for k in REQUIRED:
        if k not in data:
            fail(f"missing field: {k}")

    if data["mutation_performed"] is not False:
        fail("mutation_performed must be false for Phase 3.2")

    if data["execution_performed"] is not False:
        fail("execution_performed must be false for Phase 3.2")

    if data["state"] not in ["APPLIED", "BLOCKED", "FAILED_VALIDATION", "ROLLED_BACK", "HALTED_FOR_APPROVAL"]:
        fail("invalid state")

    print(f"[PASS] apply journal valid: {args.journal}")

if __name__ == "__main__":
    main()
