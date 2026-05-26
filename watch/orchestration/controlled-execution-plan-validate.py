#!/usr/bin/env python3
import json
import subprocess

REQUIRED = [
    "detect",
    "analyze",
    "classify",
    "backup",
    "bind_backup",
    "review",
    "preflight",
    "execute_spot_core_only",
    "verify",
    "rollback_or_halt",
    "journal",
]

def fail(msg):
    print(f"[FAIL] {msg}")
    raise SystemExit(1)

def ok(msg):
    print(f"[PASS] {msg}")

def main():
    p = subprocess.run(
        ["watch/orchestration/controlled-execution-plan.py", "--request-id", "validation-smoke", "--target", "fixture", "--risk", "low"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=30,
    )

    if p.returncode != 0:
        print(p.stderr)
        fail("planner failed")

    data = json.loads(p.stdout)

    if data.get("mode") != "read_only":
        fail("mode must be read_only")
    ok("read-only mode")

    if data.get("mutation_authority") is not False:
        fail("mutation_authority must be false")
    ok("no mutation authority")

    if data.get("execution_allowed") is not False:
        fail("execution_allowed must be false")
    ok("execution blocked by default")

    if data.get("executor") != "spot-core":
        fail("executor must be spot-core")
    ok("spot-core executor preserved")

    if data.get("required_chain") != REQUIRED:
        fail("required chain mismatch")
    ok("required chain preserved")

    bindings = data.get("required_bindings") or {}
    for key in [
        "backup_binding_required",
        "rollback_binding_required",
        "review_required",
        "validation_required",
        "journal_required",
    ]:
        if bindings.get(key) is not True:
            fail(f"{key} must be true")
        ok(key)

    print("RESULT: PASS")

if __name__ == "__main__":
    main()
