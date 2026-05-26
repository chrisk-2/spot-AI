#!/usr/bin/env python3
import json
import subprocess

def fail(msg):
    print(f"[FAIL] {msg}")
    raise SystemExit(1)

def ok(msg):
    print(f"[PASS] {msg}")

def main():
    p = subprocess.run(
        ["watch/runtime/observability/runtime-observability-snapshot.py"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=30,
    )

    if p.returncode != 0:
        print(p.stderr)
        fail("runtime observability snapshot command failed")

    try:
        data = json.loads(p.stdout)
    except Exception as e:
        fail(f"snapshot invalid JSON: {e!r}")

    if data.get("mode") != "read_only":
        fail("mode must be read_only")
    ok("read-only mode")

    if data.get("mutation_authority") is not False:
        fail("mutation_authority must be false")
    ok("no mutation authority")

    required = data.get("required")
    if not isinstance(required, dict):
        fail("required endpoint map missing")
    ok("required endpoint map present")

    for key in ["health", "fleet_ping", "routing", "routing_audit", "governance_events"]:
        item = required.get(key)
        if not isinstance(item, dict):
            fail(f"{key} missing")
        if item.get("ok") is not True:
            fail(f"{key} endpoint failed")
        ok(f"{key} endpoint healthy")

    optional = data.get("optional")
    if not isinstance(optional, dict):
        fail("optional endpoint map missing")
    ok("optional endpoint map present")

    print("RESULT: PASS")

if __name__ == "__main__":
    main()
