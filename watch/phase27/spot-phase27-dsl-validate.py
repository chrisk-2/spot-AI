#!/usr/bin/env python3

from pathlib import Path
import sys

REQUIRED = [
    "POLICY governance_v1",
    "INVARIANT spot_core_sole_executor = true",
    "RULE no_backup_no_execution",
    "RULE no_review_no_execution",
]

def fail(msg):
    print(f"FAIL: {msg}")
    sys.exit(1)

def main():
    path = Path("watch/governance/dsl/governance-policy-v1.dsl")

    if not path.exists():
        fail("dsl missing")

    content = path.read_text()

    missing = [x for x in REQUIRED if x not in content]

    if missing:
        fail(f"missing statements: {missing}")

    print("RESULT: PASS")
    print("governance_dsl=valid")

if __name__ == "__main__":
    main()
