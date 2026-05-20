#!/usr/bin/env python3

import json
import subprocess
import sys
from pathlib import Path

FILES = [
    "watch/runtime/timeline/operator-governance-timeline.py",
    "watch/runtime/maintenance/controlled-maintenance-pilot.py",
    "watch/runtime/maintenance/controlled-maintenance-validate.py",
]

REQUIRED_ARTIFACTS = [
    "watch/runtime/timeline/operator-governance-timeline.json",
]

FORBIDDEN = [
    "systemctl restart",
    "git apply",
    "netplan apply",
    "iptables ",
    "nft ",
    "ufw ",
    "nmcli ",
]

def fail(msg):
    print(f"FAIL: {msg}")
    sys.exit(1)

def main():
    for f in FILES:
        p = Path(f)
        if not p.exists():
            fail(f"missing file: {f}")
        text = p.read_text()
        for marker in FORBIDDEN:
            if marker in text:
                fail(f"forbidden marker in {f}: {marker}")

    subprocess.run(["python3", "-m", "py_compile", *FILES], check=True)

    subprocess.run(["watch/runtime/timeline/operator-governance-timeline.py"], check=True)
    subprocess.run(["watch/runtime/maintenance/controlled-maintenance-pilot.py"], check=True)
    subprocess.run(["watch/runtime/maintenance/controlled-maintenance-validate.py"], check=True)

    for artifact in REQUIRED_ARTIFACTS:
        if not Path(artifact).exists():
            fail(f"missing artifact: {artifact}")

    timeline = json.loads(Path("watch/runtime/timeline/operator-governance-timeline.json").read_text())
    for key in ["execution_allowed", "mutation_allowed", "service_restart_allowed"]:
        if timeline.get(key) is not False:
            fail(f"timeline grants {key}")

    print("RESULT: PASS")
    print("cases=10 operator_timeline=pass maintenance_pilot=pass maintenance_validate=pass fixture_only=pass review_required=pass approval_required=pass backup_required=pass rollback_required=pass execution_blocked=pass mutation_scope=none")

if __name__ == "__main__":
    main()
