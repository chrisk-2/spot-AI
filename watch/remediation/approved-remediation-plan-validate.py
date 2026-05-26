#!/usr/bin/env python3
import json
import subprocess
import sys

p = subprocess.run(
    ["python3", "watch/remediation/approved-remediation-plan-snapshot.py"],
    text=True,
    capture_output=True,
)

if p.returncode != 0:
    print("RESULT: FAIL")
    print(p.stderr.strip())
    sys.exit(1)

try:
    data = json.loads(p.stdout)
except Exception as e:
    print("RESULT: FAIL")
    print(f"invalid json: {e}")
    sys.exit(1)

errors = []

if data.get("mode") != "read_only":
    errors.append("mode must be read_only")
if data.get("advisory_only") is not True:
    errors.append("advisory_only must be true")
if data.get("execution_allowed") is not False:
    errors.append("execution_allowed must be false")
if data.get("mutation_authority") is not False:
    errors.append("mutation_authority must be false")
if data.get("executor") != "spot-core":
    errors.append("executor must be spot-core")

schema = data.get("plan_schema", {})
for key, value in schema.items():
    if value is not True:
        errors.append(f"plan_schema.{key} must be true")

authority = data.get("execution_authority", {})
if authority.get("spot-core") != "allowed_after_all_gates":
    errors.append("spot-core must be allowed_after_all_gates")

for actor, value in authority.items():
    if actor != "spot-core" and value != "forbidden":
        errors.append(f"{actor} must be forbidden")

required_missing = {
    "execution_lease",
    "review_verdict",
    "backup_binding",
    "rollback_binding",
    "validation_command",
    "journal_target",
}

if set(data.get("blocked_if_missing", [])) != required_missing:
    errors.append("blocked_if_missing set mismatch")

if errors:
    print("RESULT: FAIL")
    for e in errors:
        print(f"[FAIL] {e}")
    sys.exit(1)

print("RESULT: PASS")
print("module=approved_remediation_execution_planning mode=read_only advisory_only=true execution_allowed=false mutation_authority=false executor=spot-core")
