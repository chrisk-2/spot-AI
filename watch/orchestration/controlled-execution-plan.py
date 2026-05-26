#!/usr/bin/env python3
import argparse
import json
import time

CHAIN = [
    "detect",
    "analyze",
    "classify",
    "backup",
    "bind_backup",
    "review",
    "preflight",
    "execute_spot_core_only",
    "verify",
    "rollback_or_halt",
    "journal",
]

def main():
    ap = argparse.ArgumentParser(description="Create read-only controlled execution orchestration plan.")
    ap.add_argument("--request-id", default="manual-readonly-plan")
    ap.add_argument("--target", default="unspecified")
    ap.add_argument("--risk", default="low", choices=["low", "medium", "high"])
    ap.add_argument("--action", default="read-only planning")
    args = ap.parse_args()

    approval_required = args.risk == "high"

    out = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "mode": "read_only",
        "mutation_authority": False,
        "execution_allowed": False,
        "executor": "spot-core",
        "request_id": args.request_id,
        "target": args.target,
        "risk": args.risk,
        "action": args.action,
        "approval_required": approval_required,
        "required_chain": CHAIN,
        "required_bindings": {
            "backup_binding_required": True,
            "rollback_binding_required": True,
            "review_required": True,
            "validation_required": True,
            "journal_required": True,
        },
        "blocked_until": [
            "backup_verified",
            "rollback_defined",
            "review_passed",
            "preflight_passed",
            "operator_or_policy_authorized",
        ],
    }

    print(json.dumps(out, indent=2, sort_keys=True))

if __name__ == "__main__":
    main()
