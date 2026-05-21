#!/usr/bin/env python3
import json
import sys
from pathlib import Path

REQUIRED = [
    "schema_version",
    "event_id",
    "ts",
    "event_type",
    "authority",
    "source",
    "correlation",
    "subject",
    "decision",
    "integrity",
]

def validate_event(obj):
    errors = []

    for key in REQUIRED:
        if key not in obj:
            errors.append(f"missing {key}")

    if obj.get("schema_version") != "spot.governance.event.v1":
        errors.append("invalid schema_version")

    authority = obj.get("authority", {})
    if authority.get("executor") != "spot-core":
        errors.append("executor must be spot-core")
    if authority.get("mutation_authority") is not False:
        errors.append("mutation_authority must be false")
    if authority.get("worker_self_apply_allowed") is not False:
        errors.append("worker_self_apply_allowed must be false")

    integrity = obj.get("integrity", {})
    if integrity.get("read_only") is not True:
        errors.append("integrity.read_only must be true")

    return errors

def main():
    fail = 0
    count = 0

    for line in sys.stdin:
        if not line.strip():
            continue
        count += 1
        try:
            obj = json.loads(line)
        except Exception as e:
            print(f"FAIL invalid json line {count}: {e}")
            fail += 1
            continue

        errors = validate_event(obj)
        if errors:
            print(f"FAIL event {count}: {'; '.join(errors)}")
            fail += 1

    print(f"RESULT: {'FAIL' if fail else 'PASS'} count={count} fail={fail}")
    return 1 if fail else 0

if __name__ == "__main__":
    raise SystemExit(main())
