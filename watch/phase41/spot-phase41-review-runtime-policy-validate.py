#!/usr/bin/env python3

import json
import sys
from pathlib import Path

POLICY = Path("watch/runtime/review/review-runtime-policy.json")

def fail(msg):
    print(f"FAIL: {msg}")
    sys.exit(1)

def main():
    data = json.loads(POLICY.read_text())
    p = data["review_runtime_policy"]

    if p["default_timeout_sec"] < 30:
        fail("default timeout too low")
    if p["validator_timeout_sec"] < 45:
        fail("validator timeout too low")
    if p["max_concurrent_reviews"] != 1:
        fail("review concurrency must be 1")
    if p["execution_authority"] is not False:
        fail("review policy grants execution authority")
    if p["mutation_authority"] is not False:
        fail("review policy grants mutation authority")

    for name, cfg in data["reviewers"].items():
        if cfg["can_execute"] is not False:
            fail(f"reviewer can_execute violation: {name}")
        if cfg["can_self_apply"] is not False:
            fail(f"reviewer can_self_apply violation: {name}")

    print("RESULT: PASS")
    print("review_runtime_policy=valid")

if __name__ == "__main__":
    main()
