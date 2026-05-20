#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

SIM = Path("watch/phase5/spot-sandbox-mutation-sim.py")

CASES = [
    "sandbox_mutation_success",
    "sandbox_verification_failed_rollback",
    "sandbox_backup_missing_blocked",
    "sandbox_rollback_missing_blocked",
    "sandbox_replay_blocked",
    "sandbox_target_escape_blocked",
]

REQUIRED_KEYS = {
    "receipt_id",
    "created_at",
    "request_id",
    "execution_id",
    "lease_id",
    "envelope_id",
    "replay_guard",
    "phase",
    "executor",
    "action_type",
    "risk_class",
    "case",
    "target",
    "sandbox_root",
    "backup_path",
    "rollback_path",
    "blocked_reason",
    "backup_created",
    "backup_verified",
    "rollback_defined",
    "mutation_performed",
    "verification_performed",
    "verification_passed",
    "rollback_performed",
    "rollback_verified",
    "replay_guard_checked",
    "replay_detected",
    "target_escape_detected",
    "git_apply_performed",
    "service_restart_performed",
    "worker_execution_performed",
    "final_outcome",
}


def require(cond: bool, msg: str) -> None:
    if not cond:
        raise SystemExit(f"[FAIL] {msg}")


def canonical(obj: dict) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def run_case(case: str) -> dict:
    p = subprocess.run(
        [
            sys.executable,
            str(SIM),
            "--request-id",
            f"phase5-validate-{case}",
            "--case",
            case,
        ],
        text=True,
        capture_output=True,
        check=False,
    )

    require(p.returncode == 0, f"{case}: simulator failed: {p.stderr}")

    receipt_path = Path(p.stdout.strip())
    require(receipt_path.exists(), f"{case}: receipt missing: {receipt_path}")

    return json.loads(receipt_path.read_text())


def validate_common(case: str, r: dict) -> None:
    missing = REQUIRED_KEYS - set(r)
    require(not missing, f"{case}: missing keys: {sorted(missing)}")

    require(r["phase"] == "5", f"{case}: wrong phase")
    require(r["executor"] == "spot-core", f"{case}: executor must be spot-core")
    require(r["action_type"] == "sandbox_mutation", f"{case}: wrong action_type")
    require(r["risk_class"] == "sandbox", f"{case}: wrong risk_class")
    require(r["case"] == case, f"{case}: case mismatch")

    require(r["git_apply_performed"] is False, f"{case}: git apply forbidden")
    require(r["service_restart_performed"] is False, f"{case}: service restart forbidden")
    require(r["worker_execution_performed"] is False, f"{case}: worker execution forbidden")
    require(r["replay_guard_checked"] is True, f"{case}: replay guard not checked")

    require(str(r["receipt_id"]).startswith("RECEIPT-"), f"{case}: bad receipt_id")
    require(str(r["execution_id"]).startswith("EXEC-"), f"{case}: bad execution_id")
    require(str(r["lease_id"]).startswith("LEASE-"), f"{case}: bad lease_id")
    require(str(r["envelope_id"]).startswith("ENV-"), f"{case}: bad envelope_id")
    require(isinstance(r["replay_guard"], str) and len(r["replay_guard"]) == 24, f"{case}: bad replay_guard")


def validate_case(case: str, r: dict) -> None:
    validate_common(case, r)

    expected = {
        "sandbox_mutation_success": {
            "blocked_reason": None,
            "backup_created": True,
            "backup_verified": True,
            "rollback_defined": True,
            "mutation_performed": True,
            "verification_performed": True,
            "verification_passed": True,
            "rollback_performed": False,
            "rollback_verified": False,
            "replay_detected": False,
            "target_escape_detected": False,
            "final_outcome": "success",
        },
        "sandbox_verification_failed_rollback": {
            "blocked_reason": None,
            "backup_created": True,
            "backup_verified": True,
            "rollback_defined": True,
            "mutation_performed": True,
            "verification_performed": True,
            "verification_passed": False,
            "rollback_performed": True,
            "rollback_verified": True,
            "replay_detected": False,
            "target_escape_detected": False,
            "final_outcome": "rolled_back",
        },
        "sandbox_backup_missing_blocked": {
            "blocked_reason": "backup_missing",
            "backup_created": False,
            "backup_verified": False,
            "rollback_defined": False,
            "mutation_performed": False,
            "verification_performed": False,
            "verification_passed": False,
            "rollback_performed": False,
            "rollback_verified": False,
            "replay_detected": False,
            "target_escape_detected": False,
            "final_outcome": "blocked",
        },
        "sandbox_rollback_missing_blocked": {
            "blocked_reason": "rollback_missing",
            "backup_created": True,
            "backup_verified": True,
            "rollback_defined": False,
            "mutation_performed": False,
            "verification_performed": False,
            "verification_passed": False,
            "rollback_performed": False,
            "rollback_verified": False,
            "replay_detected": False,
            "target_escape_detected": False,
            "final_outcome": "blocked",
        },
        "sandbox_replay_blocked": {
            "blocked_reason": "replay_detected",
            "backup_created": True,
            "backup_verified": True,
            "rollback_defined": True,
            "mutation_performed": False,
            "verification_performed": False,
            "verification_passed": False,
            "rollback_performed": False,
            "rollback_verified": False,
            "replay_detected": True,
            "target_escape_detected": False,
            "final_outcome": "blocked",
        },
        "sandbox_target_escape_blocked": {
            "blocked_reason": "target_escape",
            "backup_created": False,
            "backup_verified": False,
            "rollback_defined": False,
            "mutation_performed": False,
            "verification_performed": False,
            "verification_passed": False,
            "rollback_performed": False,
            "rollback_verified": False,
            "replay_detected": False,
            "target_escape_detected": True,
            "final_outcome": "blocked",
        },
    }[case]

    for key, value in expected.items():
        require(r[key] == value, f"{case}: {key} expected {value!r}, got {r[key]!r}")


def validate_journal(records: list[dict]) -> None:
    previous_hash = "GENESIS"
    seen_execution = set()

    for index, record in enumerate(records, start=1):
        entry = {
            "index": index,
            "receipt_id": record["receipt_id"],
            "execution_id": record["execution_id"],
            "case": record["case"],
            "final_outcome": record["final_outcome"],
            "previous_hash": previous_hash,
            "mutation_performed": record["mutation_performed"],
            "rollback_performed": record["rollback_performed"],
        }
        entry_hash = sha256_text(canonical(entry))
        require(record["execution_id"] not in seen_execution, f"{record['case']}: duplicate execution_id")
        seen_execution.add(record["execution_id"])
        previous_hash = entry_hash


def main() -> None:
    require(SIM.exists(), f"missing simulator: {SIM}")

    first = []
    second = []

    for case in CASES:
        a = run_case(case)
        b = run_case(case)

        validate_case(case, a)
        validate_case(case, b)

        for key in ("receipt_id", "execution_id", "lease_id", "envelope_id", "replay_guard"):
            require(a[key] == b[key], f"{case}: {key} not deterministic")

        first.append(a)
        second.append(b)

    validate_journal(first)

    print("RESULT: PASS")
    print("cases=6 sandbox_mutation=pass rollback=pass replay_guard=pass target_escape=pass mutation_scope=sandbox_only")


if __name__ == "__main__":
    main()
