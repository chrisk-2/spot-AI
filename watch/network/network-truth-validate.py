#!/usr/bin/env python3
import json
import subprocess
import sys

def fail(msg):
    print(f"[FAIL] {msg}")
    raise SystemExit(1)

def ok(msg):
    print(f"[PASS] {msg}")

def main():
    p = subprocess.run(
        ["watch/network/network-truth-snapshot.py"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=30,
    )

    if p.returncode != 0:
        print(p.stderr)
        fail("network truth snapshot command failed")

    try:
        data = json.loads(p.stdout)
    except Exception as e:
        fail(f"snapshot invalid JSON: {e!r}")

    if data.get("mode") != "read_only":
        fail("snapshot mode must be read_only")
    ok("snapshot read-only mode")

    if data.get("mutation_authority") is not False:
        fail("mutation_authority must be false")
    ok("snapshot has no mutation authority")

    sources = data.get("sources")
    if not isinstance(sources, dict):
        fail("sources missing")
    ok("sources present")

    for key in ["spot_health", "fleet_ping", "routing", "routing_audit"]:
        item = sources.get(key)
        if not isinstance(item, dict):
            fail(f"{key} source missing")
        if item.get("ok") is not True:
            fail(f"{key} source not healthy")
        ok(f"{key} source healthy")

    for key in ["local_routes", "local_addresses", "local_dns", "local_listeners"]:
        item = sources.get(key)
        if not isinstance(item, dict):
            fail(f"{key} source missing")
        if "stdout" not in item:
            fail(f"{key} stdout missing")
        ok(f"{key} collected")

    print("RESULT: PASS")

if __name__ == "__main__":
    main()
