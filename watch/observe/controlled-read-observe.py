#!/usr/bin/env python3
"""Dormant controlled read/observe runner.

Production observation remains blocked. The only permitted execution path is
the deterministic built-in offline fixture used by the K21B validator.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import socket
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from controlled_read_observe_validation_v1 import (
    ContractError,
    validate_evidence,
    validate_request,
)

SCHEMA = "spot_controlled_read_observe_evidence_v1"
OFFLINE_OUTPUT = b"controlled read observe offline validation fixture\n"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_request(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ContractError(f"cannot load request: {exc}") from exc

    if not isinstance(payload, dict):
        raise ContractError("request top-level JSON must be an object")

    validate_request(payload)
    return payload


def evidence_base(
    request: dict[str, Any],
    started_at: str,
    completed_at: str,
) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "observation_id": request["observation_id"],
        "request_id": request["request_id"],
        "timestamp": completed_at,
        "hostname": "spot-core",
        "observer_identity": request["observer_identity"],
        "observation_class": request["observation_class"],
        "target": request["target"],
        "operation": request["operation"],
        "started_at": started_at,
        "completed_at": completed_at,
        "timeout_seconds": request["timeout_seconds"],
        "exit_status": None,
        "http_status": None,
        "output_bytes": 0,
        "output_truncated": False,
        "output_sha256": hashlib.sha256(b"").hexdigest(),
        "classification": "unknown",
        "policy_decision": "denied_fail_closed",
        "execution_allowed": False,
        "mutation_authority": False,
        "live_executor_enabled": False,
        "remediation_performed": False,
        "service_action_performed": False,
        "network_stack_mutation": False,
    }


def deny_inactive(request: dict[str, Any]) -> dict[str, Any]:
    timestamp = utc_now()
    evidence = evidence_base(request, timestamp, timestamp)
    validate_evidence(evidence)
    return evidence


def run_offline_fixture(request: dict[str, Any]) -> dict[str, Any]:
    if socket.gethostname() != "spot-core":
        raise ContractError("offline fixture host identity mismatch")

    started_at = utc_now()
    output_limit = request["output_bytes_max"]
    captured = OFFLINE_OUTPUT[:output_limit]
    truncated = len(OFFLINE_OUTPUT) > output_limit
    completed_at = utc_now()

    evidence = evidence_base(request, started_at, completed_at)
    evidence.update(
        {
            "exit_status": 0,
            "output_bytes": len(captured),
            "output_truncated": truncated,
            "output_sha256": hashlib.sha256(captured).hexdigest(),
            "classification": "healthy",
            "policy_decision": "allowed_read_only",
        }
    )

    validate_evidence(evidence)
    return evidence


def encode(record: dict[str, Any]) -> bytes:
    return (
        json.dumps(record, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def write_replay_safe(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    try:
        descriptor = os.open(
            path,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL,
            0o600,
        )
    except FileExistsError:
        if path.read_bytes() != payload:
            raise ContractError(
                "observation identity collision with different evidence"
            )
        return

    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    except BaseException:
        try:
            path.unlink()
        except OSError:
            pass
        raise


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Dormant controlled read/observe runner"
    )
    parser.add_argument("--request", required=True, type=Path)
    parser.add_argument("--evidence-dir", type=Path)
    parser.add_argument(
        "--offline-validation-fixture",
        action="store_true",
    )
    args = parser.parse_args()

    try:
        request = load_request(args.request)

        if args.offline_validation_fixture:
            evidence = run_offline_fixture(request)
        else:
            evidence = deny_inactive(request)

        payload = encode(evidence)

        if args.evidence_dir is not None:
            destination = (
                args.evidence_dir /
                f"{request['observation_id']}.json"
            )
            write_replay_safe(destination, payload)

        sys.stdout.buffer.write(payload)

        if evidence["policy_decision"] == "denied_fail_closed":
            return 3

        return 0

    except ContractError as exc:
        print(f"[DENY] controlled observation rejected: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
