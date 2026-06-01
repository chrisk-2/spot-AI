#!/usr/bin/env python3
import json
import sys
from pathlib import Path

p = Path("watch/resiliency/resiliency-model.json")
data = json.loads(p.read_text())

errors = []

if data.get("mode") != "design_only":
    errors.append("mode must be design_only")
if data.get("mutation_authority") is not False:
    errors.append("mutation_authority must be false")
if data.get("execution_allowed") is not False:
    errors.append("execution_allowed must be false")
if data.get("spot_core_executor_only") is not True:
    errors.append("spot_core_executor_only must be true")

expected = {
    "general": "spot-worker-01",
    "utility": "spot-worker-02",
    "coding": "spot-worker-03",
    "heavy": "spot-worker-04",
    "review": "spot-worker-05",
    "reasoning": "spot-worker-06",
}

if data.get("locked_roles") != expected:
    errors.append("locked role ownership drift")

for r in data.get("rehearsals", []):
    for forbidden in ("live_shutdown_allowed", "live_restore_allowed", "live_rebuild_allowed"):
        if r.get(forbidden) is True:
            errors.append(f"{r.get('name')} enables {forbidden}")

if errors:
    print("RESULT: FAIL")
    for e in errors:
        print(f"[FAIL] {e}")
    sys.exit(1)

print("RESULT: PASS")
print("[PASS] resiliency model is design-only")
print("[PASS] execution authority remains disabled")
print("[PASS] locked role ownership preserved")
