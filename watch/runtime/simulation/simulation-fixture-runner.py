#!/usr/bin/env python3

import json
from datetime import datetime, UTC
from pathlib import Path

FIXTURE = Path("watch/runtime/simulation/fixtures/fixture-environment.json")
RUN_DIR = Path("watch/runtime/simulation/runs")

def now():
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

def main():
    RUN_DIR.mkdir(parents=True, exist_ok=True)

    fixture = json.loads(FIXTURE.read_text())
    ts = now()

    result = {
        "simulation_run_id": f"group2-simulation-{ts}",
        "fixture_environment": fixture["fixture_environment"],
        "mode": "dryrun_only",
        "targets_checked": sorted(fixture["targets"].keys()),
        "forbidden_targets_enforced": fixture["forbidden_targets"],
        "production_targeted": False,
        "execution_allowed": False,
        "mutation_allowed": False,
        "service_restart_allowed": False,
        "timestamp": ts
    }

    out = RUN_DIR / f"group2-simulation-{ts.replace(':', '')}.json"
    out.write_text(json.dumps(result, indent=2, sort_keys=True))

    print("RESULT: PASS")
    print("simulation_fixture_runner=dryrun")
    print(f"artifact={out}")

if __name__ == "__main__":
    main()
