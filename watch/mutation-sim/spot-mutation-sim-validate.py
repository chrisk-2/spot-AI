#!/usr/bin/env python3

import argparse
import json
from pathlib import Path

REQUIRED = {
    "sim_id",
    "created_at",
    "transaction_id",
    "state",
    "mutation_performed",
    "execution_performed",
    "rollback_performed",
    "rollback_simulated",
    "rollback_required",
    "recovery_required",
    "replay_blocked",
}

VALID_STATES = {
    "staged_apply",
    "validation_failure",
    "rollback_transition",
    "interrupted_transaction",
    "replay_collision",
}

def fail(msg):
    raise SystemExit(f"[FAIL] {msg}")

def main():
    ap = argparse.ArgumentParser(description="Validate mutation simulator artifact.")
    ap.add_argument("--file", required=True)
    args = ap.parse_args()

    path = Path(args.file)
    if not path.exists():
        fail("artifact missing")

    data = json.loads(path.read_text())
    missing = REQUIRED - set(data)
    if missing:
        fail(f"missing fields: {sorted(missing)}")

    state = data["state"]
    if state not in VALID_STATES:
        fail("invalid state")

    if data["mutation_performed"] is not False:
        fail("mutation_performed must remain false")
    if data["execution_performed"] is not False:
        fail("execution_performed must remain false")
    if data["rollback_performed"] is not False:
        fail("rollback_performed must remain false")

    expected = {
        "staged_apply": {
            "rollback_required": False,
            "rollback_simulated": False,
            "recovery_required": False,
            "replay_blocked": False,
        },
        "validation_failure": {
            "rollback_required": True,
            "rollback_simulated": False,
            "recovery_required": False,
            "replay_blocked": False,
        },
        "rollback_transition": {
            "rollback_required": True,
            "rollback_simulated": True,
            "recovery_required": False,
            "replay_blocked": False,
        },
        "interrupted_transaction": {
            "rollback_required": False,
            "rollback_simulated": False,
            "recovery_required": True,
            "replay_blocked": False,
        },
        "replay_collision": {
            "rollback_required": False,
            "rollback_simulated": False,
            "recovery_required": False,
            "replay_blocked": True,
        },
    }

    for key, value in expected[state].items():
        if data.get(key) is not value:
            fail(f"{state}: {key} must be {value}")

    print(f"[PASS] mutation simulator valid: {path}")

if __name__ == "__main__":
    main()
