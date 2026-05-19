#!/usr/bin/env python3

import argparse
import json
from pathlib import Path

REQUIRED = {
    "wrapper_proof_id",
    "created_at",
    "phase",
    "source_proof_id",
    "case",
    "wrapper_allowed",
    "rejection_reason",
    "mutation_performed",
    "execution_performed",
    "rollback_performed",
    "git_apply_performed",
    "service_restart_performed",
    "spot_core_sole_executor",
    "worker_self_apply_allowed",
    "codex_mutation_allowed",
    "openai_mutation_allowed",
}

CASES = {
    "safe_envelope",
    "unsafe_mutation",
    "unsafe_execution",
    "unsafe_rollback",
    "executor_drift",
    "worker_self_apply",
    "codex_mutation",
    "openai_mutation",
}

REJECTION_REASON = {
    "safe_envelope": None,
    "unsafe_mutation": "unsafe_mutation",
    "unsafe_execution": "unsafe_execution",
    "unsafe_rollback": "unsafe_rollback",
    "executor_drift": "executor_drift",
    "worker_self_apply": "worker_self_apply",
    "codex_mutation": "codex_mutation",
    "openai_mutation": "openai_mutation",
}

def fail(msg):
    raise SystemExit(f"[FAIL] {msg}")

def main():
    ap = argparse.ArgumentParser(description="Validate dry-run apply-wrapper integration proof.")
    ap.add_argument("--file", required=True)
    args = ap.parse_args()

    p = Path(args.file)
    if not p.exists():
        fail("proof missing")

    data = json.loads(p.read_text())
    missing = REQUIRED - set(data)
    if missing:
        fail(f"missing fields: {sorted(missing)}")

    case = data["case"]
    if case not in CASES:
        fail("invalid case")

    if data["phase"] != "3.12":
        fail("phase must be 3.12")

    if data["rejection_reason"] != REJECTION_REASON[case]:
        fail(f"{case}: invalid rejection_reason")

    if case == "safe_envelope":
        if data["wrapper_allowed"] is not True:
            fail("safe_envelope must be allowed")
    else:
        if data["wrapper_allowed"] is not False:
            fail(f"{case} must be rejected")

    for key in (
        "mutation_performed",
        "execution_performed",
        "rollback_performed",
        "git_apply_performed",
        "service_restart_performed",
        "worker_self_apply_allowed",
        "codex_mutation_allowed",
        "openai_mutation_allowed",
    ):
        if data[key] is not False:
            fail(f"{key} must remain false")

    if data["spot_core_sole_executor"] is not True:
        fail("spot_core_sole_executor must remain true")

    print(f"[PASS] apply-wrapper proof valid: {p}")

if __name__ == "__main__":
    main()
