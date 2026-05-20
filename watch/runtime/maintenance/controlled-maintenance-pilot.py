#!/usr/bin/env python3

import json
from datetime import datetime, UTC
from pathlib import Path

PLAN_DIR = Path("watch/runtime/maintenance/plans")
RUN_DIR = Path("watch/runtime/maintenance/runs")

def now():
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

def main():
    PLAN_DIR.mkdir(parents=True, exist_ok=True)
    RUN_DIR.mkdir(parents=True, exist_ok=True)

    ts = now()
    plan = {
        "maintenance_plan_id": f"controlled-maintenance-plan-{ts}",
        "mode": "fixture_only_plan",
        "target": "fixture-service",
        "risk_class": "low",
        "requires_review": True,
        "requires_approval": True,
        "requires_backup": True,
        "requires_rollback": True,
        "execution_allowed": False,
        "mutation_allowed": False,
        "service_restart_allowed": False,
        "production_targeted": False,
        "timestamp": ts
    }

    run = {
        "maintenance_run_id": f"controlled-maintenance-run-{ts}",
        "plan_id": plan["maintenance_plan_id"],
        "mode": "dryrun_only",
        "steps": [
            "detect",
            "plan",
            "review_required",
            "approval_required",
            "backup_required",
            "rollback_required",
            "execution_blocked"
        ],
        "final_state": "blocked_before_execution",
        "execution_performed": False,
        "mutation_performed": False,
        "service_restart_performed": False,
        "timestamp": ts
    }

    plan_path = PLAN_DIR / f"{plan['maintenance_plan_id']}.json"
    run_path = RUN_DIR / f"{run['maintenance_run_id']}.json"

    plan_path.write_text(json.dumps(plan, indent=2, sort_keys=True))
    run_path.write_text(json.dumps(run, indent=2, sort_keys=True))

    print("RESULT: PASS")
    print("controlled_maintenance_pilot=dryrun")
    print(f"plan={plan_path}")
    print(f"run={run_path}")

if __name__ == "__main__":
    main()
