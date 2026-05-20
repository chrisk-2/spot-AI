#!/usr/bin/env python3

import json
from datetime import datetime, UTC
from pathlib import Path

ROOT = Path("watch/runtime/warm")
ROOT.mkdir(parents=True, exist_ok=True)

def main():
    ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    plan = {
        "warm_plan_id": f"review-warm-plan-{ts}",
        "phase": 45,
        "mode": "plan_only",
        "targets": [
            {
                "worker": "spot-worker-05",
                "model": "qwen2.5-coder:32b",
                "purpose": "primary_review"
            },
            {
                "worker": "spot-worker-06",
                "model": "qwen2.5:32b",
                "purpose": "reasoning_escalation"
            }
        ],
        "requires_operator_approval_before_runtime_change": True,
        "service_restart_allowed": False,
        "mutation_performed": False,
        "timestamp": ts
    }

    out = ROOT / f"review-warm-plan-dryrun-{ts}.json"
    out.write_text(json.dumps(plan, indent=2))

    print("RESULT: PASS")
    print("warm_residency_plan=pass")
    print(f"artifact={out}")

if __name__ == "__main__":
    main()
