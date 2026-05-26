#!/usr/bin/env python3
import json
import subprocess
from pathlib import Path

OUT = Path("/home/ogre/spot-stack/starfleet-ui/public/operator-status.json")

def fail(msg):
    print(f"[FAIL] {msg}")
    raise SystemExit(1)

def ok(msg):
    print(f"[PASS] {msg}")

def main():
    p = subprocess.run(
        ["watch/ui/ui-operator-status-export.py"],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=180,
    )

    if p.returncode != 0:
        print(p.stderr)
        fail("operator export failed")

    if not OUT.exists():
        fail("operator-status.json missing")
    ok("operator-status.json exists")

    try:
        data = json.loads(OUT.read_text())
    except Exception as e:
        fail(f"invalid operator-status.json: {e!r}")

    if data.get("mode") != "read_only":
        fail("mode must be read_only")
    ok("read-only mode")

    if data.get("mutation_authority") is not False:
        fail("mutation_authority must be false")
    ok("mutation authority disabled")

    checks = data.get("checks")
    if not isinstance(checks, dict):
        fail("checks missing")
    ok("checks present")

    for key in [
        "fleet_validate",
        "network_validate",
        "runtime_validate",
        "capabilities_validate",
    ]:
        item = checks.get(key)
        if not isinstance(item, dict):
            fail(f"{key} missing")
        if item.get("ok") is not True:
            fail(f"{key} failed")
        ok(f"{key} passed")

    print("RESULT: PASS")

if __name__ == "__main__":
    main()
