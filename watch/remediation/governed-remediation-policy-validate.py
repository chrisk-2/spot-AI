#!/usr/bin/env python3
import json
import subprocess

REQUIRED_CHAIN = [
    "detect",
    "classify",
    "backup_required",
    "rollback_required",
    "review_required",
    "preflight_required",
    "spot_core_execution_only",
    "verify_required",
    "journal_required",
]

def fail(msg):
    print(f"[FAIL] {msg}")
    raise SystemExit(1)

def ok(msg):
    print(f"[PASS] {msg}")

def main():
    p = subprocess.run(
        ["watch/remediation/governed-remediation-policy.py"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=30,
    )

    if p.returncode != 0:
        print(p.stderr)
        fail("policy snapshot failed")

    data = json.loads(p.stdout)

    if data.get("mode") != "read_only":
        fail("mode must be read_only")
    ok("read-only mode")

    if data.get("mutation_authority") is not False:
        fail("mutation_authority must be false")
    ok("mutation authority disabled")

    if data.get("execution_allowed") is not False:
        fail("execution_allowed must be false")
    ok("execution blocked")

    if data.get("remediation_allowed_now") is not False:
        fail("remediation_allowed_now must be false")
    ok("remediation not enabled")

    if data.get("live_mutation_allowed_now") is not False:
        fail("live_mutation_allowed_now must be false")
    ok("live mutation not enabled")

    if data.get("required_chain") != REQUIRED_CHAIN:
        fail("required chain mismatch")
    ok("required remediation chain")

    policy = data.get("policy") or {}
    for key in [
        "no_backup_no_change",
        "no_rollback_no_execution",
        "no_review_no_apply",
        "workers_do_not_self_apply",
        "spot_core_sole_executor",
        "high_risk_requires_approval",
    ]:
        if policy.get(key) is not True:
            fail(f"{key} must be true")
        ok(key)

    print("RESULT: PASS")

if __name__ == "__main__":
    main()
