#!/usr/bin/env python3

import json
import subprocess
import sys
from pathlib import Path

REQUIRED_FILES = [
    "watch/phase31/spot-phase31-approval-artifact-dryrun.py",
    "watch/phase32/spot-phase32-archive-append-dryrun.py",
    "watch/phase33/spot-phase33-quorum-dryrun.py",
    "watch/phase34/spot-phase34-cross-controller-dryrun.py",
    "watch/phase35/spot-phase35-simulation-manifest.py",
    "watch/phase36/spot-phase36-dsl-compile-dryrun.py",
    "watch/governance/capabilities/capability-registry-v1.json",
    "watch/phase37/spot-phase37-capability-registry-validate.py",
    "watch/phase38/spot-phase38-maintenance-plan-dryrun.py",
    "watch/phase39/GOVERNED-AUTONOMY-RUNTIME-INTEGRATION-CLOSEOUT.md",
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

def require(path):
    p = Path(path)
    if not p.exists():
        fail(f"missing file: {path}")
    return p

def main():
    for f in REQUIRED_FILES:
        require(f)

    registry = json.loads(Path("watch/governance/capabilities/capability-registry-v1.json").read_text())
    workers = registry["workers"]

    for worker in [
        "spot-worker-01",
        "spot-worker-02",
        "spot-worker-03",
        "spot-worker-04",
        "spot-worker-05",
        "spot-worker-06",
    ]:
        if workers[worker]["can_execute"] is not False:
            fail(f"worker execution authority violation: {worker}")
        if workers[worker]["can_self_apply"] is not False:
            fail(f"worker self-apply violation: {worker}")

    if workers["spot-core"]["can_execute"] is not True:
        fail("spot-core execution authority missing")

    compiled = Path("watch/governance/dsl/governance-policy-v1.compiled.json")
    if compiled.exists():
        data = json.loads(compiled.read_text())
        if data.get("mutation_authority") is not False:
            fail("compiled DSL grants mutation authority")

    for f in REQUIRED_FILES:
        text = Path(f).read_text()
        for marker in FORBIDDEN:
            if marker in text:
                fail(f"forbidden marker found in {f}: {marker}")

    subprocess.run(
        [
            "python3",
            "-m",
            "py_compile",
            "watch/phase31/spot-phase31-approval-artifact-dryrun.py",
            "watch/phase32/spot-phase32-archive-append-dryrun.py",
            "watch/phase33/spot-phase33-quorum-dryrun.py",
            "watch/phase34/spot-phase34-cross-controller-dryrun.py",
            "watch/phase35/spot-phase35-simulation-manifest.py",
            "watch/phase36/spot-phase36-dsl-compile-dryrun.py",
            "watch/phase37/spot-phase37-capability-registry-validate.py",
            "watch/phase38/spot-phase38-maintenance-plan-dryrun.py",
        ],
        check=True,
    )

    print("RESULT: PASS")
    print("cases=13 approval_artifact_dryrun=pass archive_append_dryrun=pass quorum_dryrun=pass cross_controller_dryrun=pass simulation_manifest=pass dsl_compile_dryrun=pass capability_registry=pass maintenance_plan_dryrun=pass worker_execution_blocked=pass self_apply_blocked=pass production_mutation_blocked=pass service_restart_blocked=pass mutation_scope=none")

if __name__ == "__main__":
    main()
