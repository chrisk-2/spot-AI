#!/usr/bin/env python3

import json
import sys
from pathlib import Path

PLAN_DIR = Path("watch/runtime/maintenance/plans")
RUN_DIR = Path("watch/runtime/maintenance/runs")

def fail(msg):
    print(f"FAIL: {msg}")
    sys.exit(1)

def main():
    plans = sorted(PLAN_DIR.glob("controlled-maintenance-plan-*.json"))
    runs = sorted(RUN_DIR.glob("controlled-maintenance-run-*.json"))

    if not plans:
        fail("no maintenance plans found")
    if not runs:
        fail("no maintenance runs found")

    plan = json.loads(plans[-1].read_text())
    run = json.loads(runs[-1].read_text())

    if plan.get("production_targeted") is not False:
        fail("maintenance plan targeted production")

    for key in ["execution_allowed", "mutation_allowed", "service_restart_allowed"]:
        if plan.get(key) is not False:
            fail(f"maintenance plan grants {key}")

    for key in ["execution_performed", "mutation_performed", "service_restart_performed"]:
        if run.get(key) is not False:
            fail(f"maintenance run performed {key}")

    if run.get("final_state") != "blocked_before_execution":
        fail("maintenance run did not block before execution")

    print("RESULT: PASS")
    print("controlled_maintenance=valid")
    print(f"plans={len(plans)} runs={len(runs)}")

if __name__ == "__main__":
    main()
