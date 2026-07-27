#!/usr/bin/env python3
"""Validate the Module 49 Controlled Hands no-op contract."""

import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

CONTRACT = Path(__file__).with_name("controlled-hands-noop.py")

SAFETY_FALSE = (
    "approval_authority",
    "execution_allowed",
    "mutation_authority",
    "step6_authorized",
    "backup_created",
    "rollback_executed",
    "executor_dispatch_performed",
    "command_execution_performed",
    "mutation_performed",
)


def gate_fixture(ready: bool) -> dict[str, Any]:
    proposal_id = "THINK-MODULE49-VALIDATION"

    return {
        "schema_version": "1.0",
        "proposal_id": proposal_id,
        "eligibility": {
            "decision": "ELIGIBLE" if ready else "BLOCKED",
            "eligible_for_next_gate": ready,
            "proposal": {
                "proposal_id": proposal_id,
                "top_recommendation": "continue-observation-cadence",
            },
            "review": {
                "request_id": (
                    "review-module49-validation"
                    if ready
                    else None
                ),
                "verdict": "PASS" if ready else "MISSING",
                "journal_path": (
                    "/validation/review.json"
                    if ready
                    else None
                ),
            },
            "blockers": [] if ready else ["review_journal_missing"],
        },
    }


def run_contract(
    root: Path,
    name: str,
    gate: dict[str, Any],
    require_ready: bool,
) -> tuple[int, dict[str, Any], str]:
    gate_path = root / name
    payload = (
        json.dumps(gate, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")
    gate_path.write_bytes(payload)

    command = [
        sys.executable,
        str(CONTRACT),
        "--gate-record",
        str(gate_path),
    ]

    if require_ready:
        command.append("--require-ready")

    completed = subprocess.run(
        command,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    if completed.stderr:
        raise AssertionError(completed.stderr)

    record = json.loads(completed.stdout)

    return (
        completed.returncode,
        record,
        hashlib.sha256(payload).hexdigest(),
    )


def validate_common(record: dict[str, Any]) -> None:
    assert record["action"] == "ACTION_PROPOSAL"
    assert record["mode"] == "no_op"

    action = record["requested_action"]
    assert action["kind"] == "NO_OP"
    assert action["target"] is None
    assert action["argv"] == []
    assert action["shell"] is None
    assert action["executable_payload_present"] is False

    lifecycle = record["lifecycle"]
    assert lifecycle["executor_dispatch"] == "SUPPRESSED"
    assert lifecycle["system_execution"] == "NOT_PERFORMED"
    assert lifecycle["simulated_receipt"] == "NOT_CREATED"

    safety = record["safety"]
    assert safety["advisory_only"] is True
    assert safety["spot_core_sole_executor"] is True
    assert safety["worker_self_apply"] is False

    for field in SAFETY_FALSE:
        assert safety[field] is False


def main() -> int:
    assert CONTRACT.is_file()

    with tempfile.TemporaryDirectory(
        prefix="spot-module49-validation-"
    ) as directory:
        root = Path(directory)

        blocked_rc, blocked, blocked_sha = run_contract(
            root,
            "blocked.json",
            gate_fixture(False),
            True,
        )

        assert blocked_rc == 1
        assert blocked["status"] == "BLOCKED"
        assert blocked["blockers"] == ["review_journal_missing"]
        assert blocked["source"]["gate_record_sha256"] == blocked_sha
        assert blocked["lifecycle"]["proposal_intake"] == "BLOCKED"
        assert blocked["lifecycle"]["policy_gate"] == "DENIED"
        assert blocked["lifecycle"]["next_stage"] is None
        validate_common(blocked)

        print("[PASS] blocked gate fails closed")

        ready_rc, ready, ready_sha = run_contract(
            root,
            "ready.json",
            gate_fixture(True),
            True,
        )

        assert ready_rc == 0
        assert ready["status"] == "READY_FOR_NOOP_SIMULATION"
        assert ready["blockers"] == []
        assert ready["source"]["gate_record_sha256"] == ready_sha
        assert ready["lifecycle"]["proposal_intake"] == "ACCEPTED"
        assert ready["lifecycle"]["policy_gate"] == "ELIGIBLE"
        assert (
            ready["lifecycle"]["next_stage"]
            == "NOOP_RECEIPT_SIMULATION"
        )
        validate_common(ready)

        print("[PASS] eligible gate produces proposal-only no-op")

        repeat_rc, repeat, _ = run_contract(
            root,
            "ready-repeat.json",
            gate_fixture(True),
            True,
        )

        assert repeat_rc == 0
        assert repeat["action_id"] == ready["action_id"]

        print("[PASS] action identity is deterministic")
        print("[PASS] execution authority remains absent")

    print("pass=4 fail=0")
    print("RESULT: PASS")
    print("execution_allowed=false")
    print("mutation_authority=false")
    print("step6_authorized=false")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
