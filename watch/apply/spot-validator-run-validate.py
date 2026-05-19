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
    "apply_id",
    "validation_run_id",
    "validation_count",
    "passed",
    "mutation_performed",
    "execution_performed",
    "results"
]

def fail(msg):
    print(f"[FAIL] {msg}", file=sys.stderr)
    raise SystemExit(1)

def main():
    ap = argparse.ArgumentParser(description="Validate validator-run record.")
    ap.add_argument("record")
    args = ap.parse_args()

    data = json.loads(Path(args.record).read_text())

    for k in REQUIRED:
        if k not in data:
            fail(f"missing field: {k}")

    if data["mutation_performed"] is not False:
        fail("mutation_performed must be false")

    if data["execution_performed"] is not False:
        fail("execution_performed must be false")

    if not isinstance(data["results"], list):
        fail("results must be list")

    if data["validation_count"] != len(data["results"]):
        fail("validation_count mismatch")

    if data["passed"] is not all(r.get("passed") is True for r in data["results"]):
        fail("aggregate passed mismatch")

    print(f"[PASS] validator run valid: {args.record}")

if __name__ == "__main__":
    main()
