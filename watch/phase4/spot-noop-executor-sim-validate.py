#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

SIM = Path("watch/phase4/spot-noop-executor-sim.py")

CASES = [
    "allowed_noop",
    "kill_switch_blocked",
    "lease_collision",
    "interrupted_before_receipt",
    "interrupted_after_receipt",
    "stale_lease_replay",
]

REQUIRED_KEYS = {
    "receipt_id",
    "created_at",
    "request_id",
    "execution_id",
    "lease_id",
    "kill_switch_state",
    "rollback_state",
    "backup_state",
    "review_state",
    "approval_state",
    "replay_guard",
    "envelope_hash",
    "envelope_id",
    "phase",
    "executor",
    "action_type",
    "target",
    "risk_class",
    "case",
    "blocked_reason",
    "mutation_performed",
    "execution_performed",
    "noop_performed",
    "rollback_required",
    "rollback_performed",
    "kill_switch_checked",
    "lease_checked",
    "lease_valid",
    "receipt_valid",
    "replay_guard_checked",
    "replay_detected",
    "recovery_state",
    "git_apply_performed",
    "service_restart_performed",
    "final_outcome",
}


def require(cond: bool, msg: str) -> None:
    if not cond:
        raise SystemExit(f"[FAIL] {msg}")


def run_case(case: str) -> dict:
    p = subprocess.run(
        [
            sys.executable,
            str(SIM),
            "--request-id",
            f"phase4-validate-{case}",
            "--case",
            case,
        ],
        text=True,
        capture_output=True,
        check=False,
    )

    if p.returncode != 0:
        raise SystemExit(f"[FAIL] {case}: simulator exited {p.returncode}\n{p.stderr}")

    receipt_path = Path(p.stdout.strip())
    require(receipt_path.exists(), f"{case}: receipt path not found: {receipt_path}")

    try:
        return json.loads(receipt_path.read_text())
    except json.JSONDecodeError as e:
        raise SystemExit(f"[FAIL] {case}: invalid receipt JSON: {e}\n{receipt_path}")


def validate_common(case: str, r: dict) -> None:
    missing = REQUIRED_KEYS - set(r)
    require(not missing, f"{case}: missing receipt keys: {sorted(missing)}")

    require(r["phase"] == "4", f"{case}: wrong phase")
    require(r["executor"] == "spot-core", f"{case}: executor must be spot-core")
    require(r["action_type"] == "noop", f"{case}: action_type must be noop")
    require(r["risk_class"] == "none", f"{case}: risk_class must be none")
    require(r["approval_state"] == "not_required", f"{case}: approval_state must be not_required")
    require(r["review_state"] == "pass", f"{case}: review_state must be pass")
    require(r["backup_state"] == "not_required", f"{case}: backup_state must be not_required")
    require(r["rollback_state"] == "not_required", f"{case}: rollback_state must be not_required")
    require(r["case"] == case, f"{case}: case mismatch")

    require(r["mutation_performed"] is False, f"{case}: mutation_performed must be false")
    require(r["rollback_required"] is False, f"{case}: rollback_required must be false")
    require(r["rollback_performed"] is False, f"{case}: rollback_performed must be false")
    require(r["git_apply_performed"] is False, f"{case}: git_apply_performed must be false")
    require(r["service_restart_performed"] is False, f"{case}: service_restart_performed must be false")

    require(r["kill_switch_checked"] is True, f"{case}: kill switch must be checked")
    require(r["lease_checked"] is True, f"{case}: lease must be checked")
    require(r["replay_guard_checked"] is True, f"{case}: replay guard must be checked")

    require(isinstance(r["receipt_id"], str) and r["receipt_id"].startswith("RECEIPT-"), f"{case}: bad receipt_id")
    require(isinstance(r["execution_id"], str) and r["execution_id"].startswith("EXEC-"), f"{case}: bad execution_id")
    require(isinstance(r["lease_id"], str) and r["lease_id"].startswith("LEASE-"), f"{case}: bad lease_id")
    require(isinstance(r["envelope_id"], str) and r["envelope_id"].startswith("ENV-"), f"{case}: bad envelope_id")
    require(isinstance(r["envelope_hash"], str) and len(r["envelope_hash"]) == 16, f"{case}: bad envelope_hash")
    require(isinstance(r["replay_guard"], str) and len(r["replay_guard"]) == 24, f"{case}: bad replay_guard")


def validate_case(case: str, r: dict) -> None:
    validate_common(case, r)

    expected = {
        "allowed_noop": {
            "kill_switch_state": "clear",
            "blocked_reason": None,
            "execution_performed": True,
            "noop_performed": True,
            "lease_valid": True,
            "receipt_valid": True,
            "replay_detected": False,
            "recovery_state": "clean_success",
            "final_outcome": "success",
        },
        "kill_switch_blocked": {
            "blocked_reason": "kill_switch_active",
            "kill_switch_state": "active",
            "execution_performed": False,
            "noop_performed": False,
            "lease_valid": True,
            "receipt_valid": True,
            "replay_detected": False,
            "recovery_state": "clean_blocked",
            "final_outcome": "blocked",
        },
        "lease_collision": {
            "kill_switch_state": "clear",
            "blocked_reason": "lease_collision",
            "execution_performed": False,
            "noop_performed": False,
            "lease_valid": False,
            "receipt_valid": True,
            "replay_detected": False,
            "recovery_state": "clean_blocked",
            "final_outcome": "blocked",
        },
        "interrupted_before_receipt": {
            "kill_switch_state": "clear",
            "blocked_reason": "interrupted_before_receipt",
            "execution_performed": False,
            "noop_performed": False,
            "lease_valid": True,
            "receipt_valid": False,
            "replay_detected": False,
            "recovery_state": "incomplete_before_receipt",
            "final_outcome": "blocked",
        },
        "interrupted_after_receipt": {
            "kill_switch_state": "clear",
            "blocked_reason": None,
            "execution_performed": True,
            "noop_performed": True,
            "lease_valid": True,
            "receipt_valid": True,
            "replay_detected": False,
            "recovery_state": "clean_success",
            "final_outcome": "success",
        },
        "stale_lease_replay": {
            "kill_switch_state": "clear",
            "blocked_reason": "stale_lease",
            "execution_performed": False,
            "noop_performed": False,
            "lease_valid": False,
            "receipt_valid": True,
            "replay_detected": True,
            "recovery_state": "stale_lease",
            "final_outcome": "blocked",
        },
    }[case]

    for key, value in expected.items():
        require(r[key] == value, f"{case}: {key} expected {value!r}, got {r[key]!r}")


def main() -> None:
    require(SIM.exists(), f"missing simulator: {SIM}")

    first = {}
    second = {}

    for case in CASES:
        first[case] = run_case(case)
        second[case] = run_case(case)

        validate_case(case, first[case])
        validate_case(case, second[case])

        for key in ("receipt_id", "execution_id", "lease_id"):
            require(
                first[case][key] == second[case][key],
                f"{case}: {key} is not deterministic",
            )

    print("RESULT: PASS")
    print("cases=6 immutable_receipts=pass deterministic_execution_identity=pass recovery=pass mutation=none")


if __name__ == "__main__":
    main()
