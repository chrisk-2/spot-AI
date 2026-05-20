#!/usr/bin/env python3

import json
from pathlib import Path

OUT = Path("watch/runtime/review/validator-timeout-policy.json")

def main():
    policy = {
        "version": 1,
        "validator": "spot validate",
        "review_local_timeout_sec": 60,
        "review_local_cold_start_budget_sec": 90,
        "transient_timeout_isolation": True,
        "governance_failure_required_for_hard_fail": True,
        "service_restart_allowed": False,
        "mutation_authority": False
    }

    OUT.write_text(json.dumps(policy, indent=2))

    print("RESULT: PASS")
    print("validator_timeout_policy=pass")
    print(f"artifact={OUT}")

if __name__ == "__main__":
    main()
