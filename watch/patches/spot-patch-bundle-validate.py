#!/usr/bin/env python3
import argparse
import json
import sys
from pathlib import Path

REQUIRED_TOP = [
    "schema_version",
    "request_id",
    "patch_bundle_id",
    "phase",
    "created_utc",
    "generated_by",
    "target",
    "risk_class",
    "intent",
    "files",
    "diff_artifacts",
    "validation",
    "rollback",
    "review_required",
    "execution_allowed",
]

def fail(msg):
    print(f"[FAIL] {msg}", file=sys.stderr)
    raise SystemExit(1)

def main():
    ap = argparse.ArgumentParser(description="Validate Spot patch bundle schema.")
    ap.add_argument("bundle")
    args = ap.parse_args()

    p = Path(args.bundle)
    data = json.loads(p.read_text())

    for k in REQUIRED_TOP:
        if k not in data:
            fail(f"missing field: {k}")

    if data["execution_allowed"] is not False:
        fail("execution_allowed must be false for patch bundles")

    if data["review_required"] is not True:
        fail("review_required must be true")

    if data["risk_class"] not in ["low", "medium", "high"]:
        fail("invalid risk_class")

    if not isinstance(data["files"], list):
        fail("files must be list")

    if not isinstance(data["validation"], list):
        fail("validation must be list")

    rb = data["rollback"]
    if not isinstance(rb, dict) or rb.get("required") is not True or not rb.get("strategy"):
        fail("rollback required/strategy invalid")

    print(f"[PASS] patch bundle valid: {p}")

if __name__ == "__main__":
    main()
