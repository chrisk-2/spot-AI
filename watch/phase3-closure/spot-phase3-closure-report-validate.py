#!/usr/bin/env python3

import argparse
import json
from pathlib import Path

REQUIRED = {
    "closure_id",
    "created_at",
    "phase",
    "branch",
    "head",
    "phase3_proof_id",
    "apply_wrapper_proof_id",
    "validation_expected",
    "mutation_performed",
    "execution_performed",
    "rollback_performed",
    "git_apply_enabled",
    "config_mutation_enabled",
    "service_restart_enabled",
    "rollback_restore_enabled",
    "spot_core_sole_executor",
    "worker_self_apply_allowed",
    "codex_mutation_allowed",
    "openai_mutation_allowed",
    "next_live_gate_recommendation",
    "inputs",
}

def fail(msg):
    raise SystemExit(f"[FAIL] {msg}")

def main():
    ap = argparse.ArgumentParser(description="Validate Phase 3 closure report.")
    ap.add_argument("--file", required=True)
    args = ap.parse_args()

    p = Path(args.file)
    if not p.exists():
        fail("closure report missing")

    data = json.loads(p.read_text())
    missing = REQUIRED - set(data)
    if missing:
        fail(f"missing fields: {sorted(missing)}")

    if data["phase"] != "3.13":
        fail("phase must be 3.13")

    expected = data["validation_expected"]
    if expected.get("pass") != 30 or expected.get("warn") != 0 or expected.get("fail") != 0:
        fail("validation expectation must be pass=30 warn=0 fail=0")

    false_keys = (
        "mutation_performed",
        "execution_performed",
        "rollback_performed",
        "git_apply_enabled",
        "config_mutation_enabled",
        "service_restart_enabled",
        "rollback_restore_enabled",
        "worker_self_apply_allowed",
        "codex_mutation_allowed",
        "openai_mutation_allowed",
    )

    for key in false_keys:
        if data[key] is not False:
            fail(f"{key} must remain false")

    if data["spot_core_sole_executor"] is not True:
        fail("spot_core_sole_executor must remain true")

    if not data["next_live_gate_recommendation"]:
        fail("next_live_gate_recommendation missing")

    print(f"[PASS] Phase 3 closure report valid: {p}")

if __name__ == "__main__":
    main()
