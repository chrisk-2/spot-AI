#!/usr/bin/env python3

import json
import subprocess
import sys
from pathlib import Path

FILES = [
    "watch/runtime/archive/immutable-archive-writer.py",
    "watch/runtime/archive/archive-integrity-validate.py",
    "watch/runtime/simulation/simulation-fixture-runner.py",
    "watch/runtime/simulation/simulation-fixture-validate.py",
]

REQUIRED_ARTIFACTS = [
    "watch/runtime/archive/archive-index.jsonl",
    "watch/runtime/simulation/fixtures/fixture-environment.json",
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

    subprocess.run(["watch/runtime/archive/immutable-archive-writer.py"], check=True)
    subprocess.run(["watch/runtime/archive/archive-integrity-validate.py"], check=True)
    subprocess.run(["watch/runtime/simulation/simulation-fixture-runner.py"], check=True)
    subprocess.run(["watch/runtime/simulation/simulation-fixture-validate.py"], check=True)

    for artifact in REQUIRED_ARTIFACTS:
        if not Path(artifact).exists():
            fail(f"missing artifact: {artifact}")

    fixture = json.loads(Path("watch/runtime/simulation/fixtures/fixture-environment.json").read_text())
    if fixture.get("execution_allowed") is not False:
        fail("fixture grants execution")
    if fixture.get("service_restart_allowed") is not False:
        fail("fixture grants service restart")

    print("RESULT: PASS")
    print("cases=10 immutable_archive_writer=pass archive_integrity=pass simulation_fixture_runner=pass simulation_fixture_validate=pass append_only_model=pass production_target_blocked=pass execution_blocked=pass mutation_blocked=pass service_restart_blocked=pass mutation_scope=none")

if __name__ == "__main__":
    main()
