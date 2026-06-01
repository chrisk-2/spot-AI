#!/usr/bin/env python3
import json
import sys
from pathlib import Path

files = [
    "worker-recovery-manifest-schema.json",
    "fleet-backup-inventory.json",
    "recovery-evidence-journal.json",
    "rebuild-validation-checklist.json"
]

errors = []

for f in files:
    p = Path("watch/resiliency") / f

    if not p.exists():
        errors.append(f"missing {f}")
        continue

    data = json.loads(p.read_text())

    if data.get("mode") != "design_only":
        errors.append(f"{f}: mode must be design_only")

    if data.get("execution_allowed") is not False:
        errors.append(f"{f}: execution_allowed must be false")

    if data.get("mutation_authority") is not False:
        errors.append(f"{f}: mutation_authority must be false")

if errors:
    print("RESULT: FAIL")
    for e in errors:
        print(f"[FAIL] {e}")
    sys.exit(1)

print("RESULT: PASS")
print("[PASS] Recovery readiness gate satisfied")
