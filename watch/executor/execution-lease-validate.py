#!/usr/bin/env python3
import json
import subprocess
import sys

cmd = ["python3", "watch/executor/execution-lease-snapshot.py"]
p = subprocess.run(cmd, text=True, capture_output=True)

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

required_false = [
    ("execution_allowed", data.get("execution_allowed")),
    ("mutation_authority", data.get("mutation_authority")),
    ("workers_may_self_apply", data.get("workers_may_self_apply")),
]

for name, value in required_false:
    if value is not False:
        errors.append(f"{name} must be false")

if data.get("mode") != "read_only":
    errors.append("mode must be read_only")

if data.get("advisory_only") is not True:
    errors.append("advisory_only must be true")

if data.get("executor") != "spot-core":
    errors.append("executor must be spot-core")

lease = data.get("lease_model", {})
for key in [
    "required_for_execution",
    "lease_owner_required",
    "lease_scope_required",
    "lease_ttl_required",
    "backup_binding_required",
    "rollback_binding_required",
    "review_binding_required",
    "journal_required",
]:
    if lease.get(key) is not True:
        errors.append(f"lease_model.{key} must be true")

expected_roles = {
    "general": "spot-worker-01",
    "utility": "spot-worker-02",
    "coding": "spot-worker-03",
    "heavy": "spot-worker-04",
    "review": "spot-worker-05",
    "reasoning": "spot-worker-06",
}

if data.get("locked_role_ownership") != expected_roles:
    errors.append("locked role ownership mismatch")

if errors:
    print("RESULT: FAIL")
    for e in errors:
        print(f"[FAIL] {e}")
    sys.exit(1)

print("RESULT: PASS")
print("module=governed_execution_leasing mode=read_only advisory_only=true execution_allowed=false mutation_authority=false executor=spot-core")
