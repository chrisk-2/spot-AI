#!/usr/bin/env python3
import json
import subprocess
import sys
from pathlib import Path

errors = []

required_files = [
    "docs/operator/MODULE-E-FLEET-RESILIENCY-HARDENING.md",
    "docs/operator/MODULE-LIVE-FLEET-REACHABILITY-VALIDATION.md",
    "watch/resiliency/resiliency-model.json",
    "watch/resiliency/resiliency-model-validate.py",
    "watch/live/live-fleet-reachability-validate.py",
]

for item in required_files:
    if not Path(item).exists():
        errors.append(f"missing required file: {item}")

model_path = Path("watch/resiliency/resiliency-model.json")
if model_path.exists():
    data = json.loads(model_path.read_text())
    expected_roles = {
        "general": "spot-worker-01",
        "utility": "spot-worker-02",
        "coding": "spot-worker-03",
        "heavy": "spot-worker-04",
        "review": "spot-worker-05",
        "reasoning": "spot-worker-06",
    }

    if data.get("mode") != "design_only":
        errors.append("resiliency model mode drift")
    if data.get("mutation_authority") is not False:
        errors.append("mutation_authority must remain false")
    if data.get("execution_allowed") is not False:
        errors.append("execution_allowed must remain false")
    if data.get("spot_core_executor_only") is not True:
        errors.append("spot_core_executor_only must remain true")
    if data.get("locked_roles") != expected_roles:
        errors.append("locked role ownership drift")

checks = [
    ["python3", "watch/resiliency/resiliency-model-validate.py"],
    ["python3", "watch/live/live-fleet-reachability-validate.py"],
]

for cmd in checks:
    result = subprocess.run(cmd, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode != 0:
        errors.append(f"check failed: {' '.join(cmd)}")
        if result.stdout:
            errors.append(result.stdout.strip())
        if result.stderr:
            errors.append(result.stderr.strip())

if errors:
    print("RESULT: FAIL")
    for error in errors:
        print(f"[FAIL] {error}")
    sys.exit(1)

print("RESULT: PASS")
print("[PASS] resiliency program files present")
print("[PASS] design-only resiliency model preserved")
print("[PASS] locked role ownership preserved")
print("[PASS] live fleet reachability passes")
print("[PASS] execution and mutation authority remain disabled")
