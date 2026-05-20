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
]

REQUIRED_KEYS = {
    "receipt_id",
    "created_at",
    "request_id",
    "execution_id",
    "lease_id",
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
    require(r["case"] == case, f"{case}: case mismatch")

    require(r["mutation_performed"] is False, f"{case}: mutation_performed must be false")
    require(r["rollback_required"] is False, f"{case}: rollback_required must be false")
    require(r["rollback_performed"] is False, f"{case}: rollback_performed must be false")
    require(r["git_apply_performed"] is False, f"{case}: git_apply_performed must be false")
    require(r["service_restart_performed"] is False, f"{case}: service_restart_performed must be false")

    require(r["kill_switch_checked"] is True, f"{case}: kill switch must be checked")
    require(r["lease_checked"] is True, f"{case}: lease must be checked")

    require(isinstance(r["receipt_id"], str) and r["receipt_id"].startswith("RECEIPT-"), f"{case}: bad receipt_id")
    require(isinstance(r["execution_id"], str) and r["execution_id"].startswith("EXEC-"), f"{case}: bad execution_id")
    require(isinstance(r["lease_id"], str) and r["lease_id"].startswith("LEASE-"), f"{case}: bad lease_id")


def validate_case(case: str, r: dict) -> None:
    validate_common(case, r)

    if case == "allowed_noop":
        require(r["blocked_reason"] is None, f"{case}: blocked_reason must be null")
        require(r["execution_performed"] is True, f"{case}: execution_performed must be true")
        require(r["noop_performed"] is True, f"{case}: noop_performed must be true")
        require(r["final_outcome"] == "success", f"{case}: final_outcome must be success")
    else:
        require(r["blocked_reason"] == case, f"{case}: blocked_reason must equal case")
        require(r["execution_performed"] is False, f"{case}: execution_performed must be false")
        require(r["noop_performed"] is False, f"{case}: noop_performed must be false")
        require(r["final_outcome"] == "blocked", f"{case}: final_outcome must be blocked")


def main() -> None:
    require(SIM.exists(), f"missing simulator: {SIM}")

    first = {}
    second = {}

    for case in CASES:
        first[case] = run_case(case)
        second[case] = run_case(case)

        validate_case(case, first[case])
        validate_case(case, second[case])

        require(
            first[case]["execution_id"] == second[case]["execution_id"],
            f"{case}: execution_id is not deterministic",
        )
        require(
            first[case]["receipt_id"] == second[case]["receipt_id"],
            f"{case}: receipt_id is not deterministic",
        )
        require(
            first[case]["lease_id"] == second[case]["lease_id"],
            f"{case}: lease_id is not deterministic",
        )

    print("RESULT: PASS")
    print("cases=3 immutable_receipts=pass deterministic_execution_identity=pass mutation=none")


if __name__ == "__main__":
    main()
