#!/usr/bin/env python3
"""Restricted service executor for Phase 2.39.

The only active operation in this phase is an allowlisted, read-only diagnosis.
The repair interface is recognized but always fails closed.

No arbitrary host, service, command, property, or systemctl action is accepted.
"""

from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
from datetime import datetime, timezone
from typing import Any

SCHEMA = "spot.restricted_service_executor.v1"
MODULE = "phase2_39_restricted_service_executor"

ALLOWED_HOST = "spot-core"
ALLOWED_SERVICE = "spot-remediation-fixture.service"
ALLOWED_OPERATIONS = ("diagnose", "repair")

SHOW_PROPERTIES = (
    "Id",
    "LoadState",
    "ActiveState",
    "SubState",
    "Result",
    "ExecMainStatus",
    "NRestarts",
)

VALIDATION_ENV = "SPOT_RESTRICTED_EXECUTOR_VALIDATION"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def base_record(operation: str, host: str, service: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "module": MODULE,
        "generated_at": utc_now(),
        "phase": "2.39",
        "mode": "restricted_dormant",
        "operation": operation,
        "target": {
            "host": host,
            "service": service,
        },
        "policy": {
            "spot_core_sole_executor": True,
            "exact_host_allowlist": [ALLOWED_HOST],
            "exact_service_allowlist": [ALLOWED_SERVICE],
            "arbitrary_command_allowed": False,
            "arbitrary_property_allowed": False,
            "remote_execution_allowed": False,
            "sudo_allowed": False,
            "shell_execution_allowed": False,
            "worker_self_apply_allowed": False,
        },
        "execution_allowed": False,
        "mutation_authority": False,
        "live_executor_enabled": False,
        "mutation_performed": False,
        "service_action_performed": False,
        "service_restart_performed": False,
        "production_service_mutation": False,
    }


def emit(record: dict[str, Any], rc: int) -> int:
    print(json.dumps(record, indent=2, sort_keys=True))
    return rc


def validate_target(
    operation: str,
    host: str,
    service: str,
) -> tuple[bool, str]:
    if operation not in ALLOWED_OPERATIONS:
        return False, "operation_not_allowlisted"

    if host != ALLOWED_HOST:
        return False, "host_not_allowlisted"

    if service != ALLOWED_SERVICE:
        return False, "service_not_allowlisted"

    validation_mode = os.environ.get(VALIDATION_ENV) == "1"

    if not validation_mode and socket.gethostname() != ALLOWED_HOST:
        return False, "executor_host_identity_mismatch"

    return True, "allowlist_match"


def parse_show_output(output: str) -> dict[str, str]:
    parsed: dict[str, str] = {}

    for line in output.splitlines():
        if "=" not in line:
            continue

        key, value = line.split("=", 1)

        if key in SHOW_PROPERTIES:
            parsed[key] = value

    return parsed


def validation_diagnosis() -> dict[str, str]:
    return {
        "Id": ALLOWED_SERVICE,
        "LoadState": "loaded",
        "ActiveState": "failed",
        "SubState": "failed",
        "Result": "exit-code",
        "ExecMainStatus": "1",
        "NRestarts": "0",
    }


def diagnose(record: dict[str, Any]) -> int:
    validation_mode = os.environ.get(VALIDATION_ENV) == "1"

    if validation_mode:
        record["status"] = "OBSERVED"
        record["result"] = {
            "ok": True,
            "source": "built_in_validation_fixture",
            "service_state": validation_diagnosis(),
        }
        return emit(record, 0)

    command = [
        "systemctl",
        "show",
        "--no-pager",
        "--property=" + ",".join(SHOW_PROPERTIES),
        ALLOWED_SERVICE,
    ]

    completed = subprocess.run(
        command,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=30,
    )

    record["status"] = (
        "OBSERVED" if completed.returncode == 0 else "DIAGNOSIS_FAILED"
    )
    record["result"] = {
        "ok": completed.returncode == 0,
        "source": "fixed_systemctl_show",
        "returncode": completed.returncode,
        "service_state": parse_show_output(completed.stdout),
        "stderr": completed.stderr.strip(),
    }

    return emit(record, 0 if completed.returncode == 0 else 2)


def repair(record: dict[str, Any]) -> int:
    record["status"] = "BLOCKED"
    record["blockers"] = [
        "repair_not_authorized_in_phase_2_39_block_c",
        "execution_allowed_false",
        "mutation_authority_false",
        "live_executor_disabled",
    ]
    record["result"] = {
        "ok": False,
        "reason": "recognized_repair_interface_fails_closed",
        "executor_dispatch_performed": False,
    }

    return emit(record, 3)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Restricted Phase 2.39 service executor"
    )
    parser.add_argument(
        "operation",
        choices=ALLOWED_OPERATIONS,
    )
    parser.add_argument(
        "--host",
        required=True,
    )
    parser.add_argument(
        "--service",
        required=True,
    )

    args = parser.parse_args()

    record = base_record(
        operation=args.operation,
        host=args.host,
        service=args.service,
    )

    allowed, reason = validate_target(
        operation=args.operation,
        host=args.host,
        service=args.service,
    )

    if not allowed:
        record["status"] = "REJECTED"
        record["result"] = {
            "ok": False,
            "reason": reason,
            "executor_dispatch_performed": False,
        }
        return emit(record, 2)

    if args.operation == "diagnose":
        return diagnose(record)

    return repair(record)


if __name__ == "__main__":
    raise SystemExit(main())
