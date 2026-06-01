#!/usr/bin/env python3
import json
import sys
from pathlib import Path

files = [
    Path("watch/resiliency/node-loss-simulation.json"),
    Path("watch/resiliency/backup-restore-drill.json"),
    Path("watch/resiliency/recovery-rehearsal-artifacts.json"),
    Path("watch/resiliency/disaster-recovery-verification.json"),
]

forbidden_true = {
    "execution_allowed",
    "mutation_authority",
    "live_shutdown_allowed",
    "live_quarantine_allowed",
    "live_restore_allowed",
    "live_rebuild_allowed",
    "backup_deletion_allowed",
}

errors = []

for path in files:
    if not path.exists():
        errors.append(f"missing {path}")
        continue

    data = json.loads(path.read_text())

    if data.get("mode") != "design_only":
        errors.append(f"{path}: mode must be design_only")

    for key in forbidden_true:
        if data.get(key) is True:
            errors.append(f"{path}: {key} must not be true")

if errors:
    print("RESULT: FAIL")
    for error in errors:
        print(f"[FAIL] {error}")
    sys.exit(1)

print("RESULT: PASS")
for path in files:
    print(f"[PASS] {path}")
print("[PASS] Modules F-J preserve design-only boundary")
