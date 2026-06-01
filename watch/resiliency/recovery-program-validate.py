#!/usr/bin/env python3

import json
import sys
from pathlib import Path

errors = []

required_docs = [
    "docs/recovery/spot-worker-01-recovery-runbook.md",
    "docs/recovery/spot-worker-02-recovery-runbook.md",
    "docs/recovery/spot-worker-03-recovery-runbook.md",
    "docs/recovery/spot-worker-04-recovery-runbook.md",
    "docs/recovery/spot-worker-05-recovery-runbook.md",
    "docs/recovery/spot-worker-06-recovery-runbook.md",
    "docs/recovery/spot-core-recovery-runbook.md",
    "docs/recovery/FLEET-DISASTER-RECOVERY-RUNBOOK.md"
]

for d in required_docs:
    if not Path(d).exists():
        errors.append(f"missing {d}")

schema = Path(
    "watch/resiliency/recovery-rehearsal-schema.json"
)

if not schema.exists():
    errors.append("missing recovery schema")
else:
    data = json.loads(schema.read_text())

    if data.get("mode") != "design_only":
        errors.append("schema mode drift")

    if data.get("execution_allowed") is not False:
        errors.append("execution authority drift")

    if data.get("mutation_authority") is not False:
        errors.append("mutation authority drift")

if errors:
    print("RESULT: FAIL")
    for e in errors:
        print(f"[FAIL] {e}")
    sys.exit(1)

print("RESULT: PASS")
print("[PASS] recovery rehearsal program valid")
