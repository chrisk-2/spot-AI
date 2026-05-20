#!/usr/bin/env python3

import json
import sys
from pathlib import Path

FIXTURE = Path("watch/runtime/simulation/fixtures/fixture-environment.json")
RUN_DIR = Path("watch/runtime/simulation/runs")

def fail(msg):
    print(f"FAIL: {msg}")
    sys.exit(1)

def main():
    if not FIXTURE.exists():
        fail("fixture missing")

    fixture = json.loads(FIXTURE.read_text())

    if fixture.get("execution_allowed") is not False:
        fail("fixture grants execution")

    if fixture.get("service_restart_allowed") is not False:
        fail("fixture grants service restart")

    for name, target in fixture.get("targets", {}).items():
        if target.get("production") is not False:
            fail(f"fixture target marked production: {name}")
        if target.get("mutation_allowed") is not False:
            fail(f"fixture target grants mutation: {name}")

    runs = sorted(RUN_DIR.glob("group2-simulation-*.json"))
    if not runs:
        fail("no simulation runs found")

    latest = json.loads(runs[-1].read_text())

    if latest.get("production_targeted") is not False:
        fail("simulation targeted production")

    if latest.get("mutation_allowed") is not False:
        fail("simulation grants mutation")

    print("RESULT: PASS")
    print("simulation_fixture=valid")
    print(f"runs={len(runs)}")

if __name__ == "__main__":
    main()
