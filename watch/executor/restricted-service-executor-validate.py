#!/usr/bin/env python3
"""Adversarial validation for the restricted Phase 2.39 executor."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

EXECUTOR = Path(__file__).with_name(
    "restricted-service-executor.py"
)

HOST = "spot-core"
SERVICE = "spot-remediation-fixture.service"

SAFETY_FALSE = (
    "execution_allowed",
    "mutation_authority",
    "live_executor_enabled",
    "mutation_performed",
    "service_action_performed",
    "service_restart_performed",
    "production_service_mutation",
)


def run(
    operation: str,
    host: str,
    service: str,
    extra: list[str] | None = None,
) -> tuple[int, dict[str, Any], str]:
    env = os.environ.copy()
    env["SPOT_RESTRICTED_EXECUTOR_VALIDATION"] = "1"

    command = [
        sys.executable,
        str(EXECUTOR),
        operation,
        "--host",
        host,
        "--service",
        service,
    ]

    if extra:
        command.extend(extra)

    completed = subprocess.run(
        command,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        timeout=30,
    )

    record: dict[str, Any] = {}

    if completed.stdout.strip():
        record = json.loads(completed.stdout)

    return completed.returncode, record, completed.stderr


def validate_safety(record: dict[str, Any]) -> None:
    assert record["schema"] == "spot.restricted_service_executor.v1"
    assert record["phase"] == "2.39"
    assert record["mode"] == "restricted_dormant"

    for key in SAFETY_FALSE:
        assert record[key] is False

    policy = record["policy"]
    assert policy["spot_core_sole_executor"] is True
    assert policy["arbitrary_command_allowed"] is False
    assert policy["arbitrary_property_allowed"] is False
    assert policy["remote_execution_allowed"] is False
    assert policy["sudo_allowed"] is False
    assert policy["shell_execution_allowed"] is False
    assert policy["worker_self_apply_allowed"] is False


def main() -> int:
    assert EXECUTOR.is_file()
    assert os.access(EXECUTOR, os.X_OK)

    source = EXECUTOR.read_text(encoding="utf-8")

    forbidden_source = (
        "shell=True",
        "os.system(",
        "subprocess.Popen(",
        '["sudo"',
        '["ssh"',
    )

    for token in forbidden_source:
        assert token not in source, token

    print("[PASS] forbidden execution surfaces absent")

    rc, diagnosis, stderr = run(
        "diagnose",
        HOST,
        SERVICE,
    )

    assert rc == 0
    assert stderr == ""
    assert diagnosis["status"] == "OBSERVED"
    assert diagnosis["result"]["ok"] is True
    assert (
        diagnosis["result"]["source"]
        == "built_in_validation_fixture"
    )
    assert diagnosis["result"]["service_state"]["ActiveState"] == "failed"
    validate_safety(diagnosis)

    print("[PASS] exact allowlisted diagnosis uses validation fixture")
    print("[PASS] validation performs no systemctl invocation")

    rc, repair, stderr = run(
        "repair",
        HOST,
        SERVICE,
    )

    assert rc == 3
    assert stderr == ""
    assert repair["status"] == "BLOCKED"
    assert repair["result"]["executor_dispatch_performed"] is False
    assert (
        "repair_not_authorized_in_phase_2_39_block_c"
        in repair["blockers"]
    )
    validate_safety(repair)

    print("[PASS] recognized repair interface fails closed")

    rc, bad_host, _ = run(
        "diagnose",
        "spot-worker-01",
        SERVICE,
    )

    assert rc == 2
    assert bad_host["status"] == "REJECTED"
    assert bad_host["result"]["reason"] == "host_not_allowlisted"
    assert bad_host["result"]["executor_dispatch_performed"] is False
    validate_safety(bad_host)

    print("[PASS] non-allowlisted host rejected")

    rc, bad_service, _ = run(
        "diagnose",
        HOST,
        "ssh.service",
    )

    assert rc == 2
    assert bad_service["status"] == "REJECTED"
    assert (
        bad_service["result"]["reason"]
        == "service_not_allowlisted"
    )
    assert (
        bad_service["result"]["executor_dispatch_performed"]
        is False
    )
    validate_safety(bad_service)

    print("[PASS] non-allowlisted service rejected")

    rc, _, stderr = run(
        "diagnose",
        HOST,
        SERVICE,
        ["--property", "FragmentPath"],
    )

    assert rc == 2
    assert "unrecognized arguments" in stderr

    print("[PASS] arbitrary property injection rejected")

    env = os.environ.copy()
    env["SPOT_RESTRICTED_EXECUTOR_VALIDATION"] = "1"

    completed = subprocess.run(
        [
            sys.executable,
            str(EXECUTOR),
            "restart",
            "--host",
            HOST,
            "--service",
            SERVICE,
        ],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        timeout=30,
    )

    assert completed.returncode == 2
    assert "invalid choice" in completed.stderr
    assert completed.stdout == ""

    print("[PASS] arbitrary operation rejected")
    print("[PASS] execution authority remains absent")
    print("pass=8 fail=0")
    print("RESULT: PASS")
    print("execution_allowed=false")
    print("mutation_authority=false")
    print("live_executor_enabled=false")
    print("service_action_performed=false")
    print("production_service_mutation=false")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
