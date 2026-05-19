#!/usr/bin/env python3

import argparse
import json
from pathlib import Path

REQUIRED = {
    "governance_id",
    "created_at",
    "transaction_id",
    "mutation_sim_id",
    "recovery_id",
    "case",
    "governance_allowed",
    "rejection_reason",
    "mutation_performed",
    "execution_performed",
    "rollback_performed",
    "spot_core_sole_executor",
    "worker_self_apply_allowed",
    "codex_mutation_allowed",
    "openai_mutation_allowed",
}

CASES = {
    "phase_mismatch",
    "unauthorized_role",
    "invalid_review_verdict",
    "missing_backup_binding",
    "missing_rollback_binding",
    "replayed_transaction",
    "stale_validator",
    "governance_drift",
    "clean_envelope",
}

REJECTION_REASON = {
    "phase_mismatch": "phase_mismatch",
    "unauthorized_role": "unauthorized_role",
    "invalid_review_verdict": "invalid_review_verdict",
    "missing_backup_binding": "missing_backup_binding",
    "missing_rollback_binding": "missing_rollback_binding",
    "replayed_transaction": "replayed_transaction",
    "stale_validator": "stale_validator",
    "governance_drift": "governance_drift",
    "clean_envelope": None,
}

def fail(msg):
    raise SystemExit(f"[FAIL] {msg}")

def main():
    ap = argparse.ArgumentParser(description="Validate governance simulator artifact.")
    ap.add_argument("--file", required=True)
    args = ap.parse_args()

    p = Path(args.file)
    if not p.exists():
        fail("artifact missing")

    data = json.loads(p.read_text())

    missing = REQUIRED - set(data)
    if missing:
        fail(f"missing fields: {sorted(missing)}")

    case = data["case"]
    if case not in CASES:
        fail("invalid governance case")

    expected_reason = REJECTION_REASON[case]

    if data["rejection_reason"] != expected_reason:
        fail(f"{case}: rejection_reason must be {expected_reason}")

    if case == "clean_envelope":
        if data["governance_allowed"] is not True:
            fail("clean_envelope must be allowed")
    else:
        if data["governance_allowed"] is not False:
            fail(f"{case} must be rejected")

    if data["mutation_performed"] is not False:
        fail("mutation_performed must remain false")
    if data["execution_performed"] is not False:
        fail("execution_performed must remain false")
    if data["rollback_performed"] is not False:
        fail("rollback_performed must remain false")

    if data["spot_core_sole_executor"] is not True:
        fail("spot_core_sole_executor must remain true")
    if data["worker_self_apply_allowed"] is not False:
        fail("worker_self_apply_allowed must remain false")
    if data["codex_mutation_allowed"] is not False:
        fail("codex_mutation_allowed must remain false")
    if data["openai_mutation_allowed"] is not False:
        fail("openai_mutation_allowed must remain false")

    print(f"[PASS] governance simulator valid: {p}")

if __name__ == "__main__":
    main()
