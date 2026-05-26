#!/usr/bin/env python3
import json
import subprocess
import sys

p = subprocess.run(
    ["python3", "watch/recovery/recovery-model-snapshot.py"],
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

model = data.get("recovery_model", {})
for key, value in model.items():
    if value is not True:
        errors.append(f"recovery_model.{key} must be true")

authority = data.get("recovery_execution_authority", {})

expected = {
    "spot-core": "allowed",
    "workers": "forbidden",
    "openai": "forbidden",
    "codex": "forbidden",
}

if authority != expected:
    errors.append("recovery_execution_authority mismatch")

if errors:
    print("RESULT: FAIL")
    for e in errors:
        print(f"[FAIL] {e}")
    sys.exit(1)

print("RESULT: PASS")
print("module=supervised_recovery_model mode=read_only advisory_only=true execution_allowed=false mutation_authority=false executor=spot-core")
