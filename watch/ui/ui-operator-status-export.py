#!/usr/bin/env python3
import json
import subprocess
import time
from pathlib import Path

ROOT = Path("/home/ogre/spot-stack")

OUT = ROOT / "starfleet-ui/public/operator-status.json"

COMMANDS = {
    "fleet_validate": "spot validate",
    "network_validate": "watch/network/network-truth-validate.py",
    "runtime_validate": "watch/runtime/observability/runtime-observability-validate.py",
    "capabilities_validate": "watch/capabilities/capability-registry-validate.py",
}

def run(cmd, timeout=120):
    try:
        p = subprocess.run(
            cmd,
            shell=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
        )

        return {
            "ok": p.returncode == 0,
            "returncode": p.returncode,
            "stdout": p.stdout.strip(),
            "stderr": p.stderr.strip(),
        }

    except Exception as e:
        return {
            "ok": False,
            "returncode": -1,
            "stdout": "",
            "stderr": repr(e),
        }

def main():
    checks = {}

    for name, cmd in COMMANDS.items():
        checks[name] = run(cmd)

    payload = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "mode": "read_only",
        "mutation_authority": False,
        "executor": "spot-core",
        "checks": checks,
    }

    OUT.write_text(json.dumps(payload, indent=2))
    print(json.dumps({
        "ok": True,
        "output": str(OUT),
        "checks": list(checks.keys()),
    }, indent=2))

if __name__ == "__main__":
    main()
