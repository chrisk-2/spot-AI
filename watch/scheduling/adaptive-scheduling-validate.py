#!/usr/bin/env python3
import json
import subprocess

ROLES = ["general", "utility", "coding", "heavy", "review", "reasoning"]

def fail(msg):
    print(f"[FAIL] {msg}")
    raise SystemExit(1)

def ok(msg):
    print(f"[PASS] {msg}")

def main():
    p = subprocess.run(
        ["watch/scheduling/adaptive-scheduling-snapshot.py"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=45,
    )

    if p.returncode != 0:
        print(p.stderr)
        fail("adaptive scheduling snapshot failed")

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

    if data.get("advisory_only") is not True:
        fail("advisory_only must be true")
    ok("advisory only")

    recs = data.get("recommendations")
    if not isinstance(recs, dict):
        fail("recommendations missing")
    ok("recommendations present")

    for role in ROLES:
        item = recs.get(role)
        if not isinstance(item, dict):
            fail(f"{role} recommendation missing")
        if item.get("role") != role:
            fail(f"{role} role mismatch")
        if item.get("advisory_only") is not True:
            fail(f"{role} must be advisory_only")
        if not item.get("recommended_worker"):
            fail(f"{role} recommended_worker missing")
        ok(f"{role} advisory recommendation")

    print("RESULT: PASS")

if __name__ == "__main__":
    main()
