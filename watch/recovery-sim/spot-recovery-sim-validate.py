#!/usr/bin/env python3

import argparse
import json
from pathlib import Path

REQUIRED = {
    "recovery_id",
    "created_at",
    "source_sim_id",
    "transaction_id",
    "state",
    "mutation_performed",
    "execution_performed",
    "rollback_performed",
    "recovery_required",
    "rehydrated",
    "replay_blocked",
    "orphan_detected",
    "stale_expired",
    "journal_chain_valid",
    "recovery_allowed",
}

VALID_STATES = {
    "interrupted_rehydrate",
    "replay_denied",
    "orphan_detected",
    "stale_expired",
    "journal_chain",
}

EXPECTED = {
    "interrupted_rehydrate": {
        "recovery_required": True,
        "rehydrated": True,
        "replay_blocked": False,
        "orphan_detected": False,
        "stale_expired": False,
        "journal_chain_valid": False,
        "recovery_allowed": False,
    },
    "replay_denied": {
        "recovery_required": False,
        "rehydrated": False,
        "replay_blocked": True,
        "orphan_detected": False,
        "stale_expired": False,
        "journal_chain_valid": False,
        "recovery_allowed": False,
    },
    "orphan_detected": {
        "recovery_required": False,
        "rehydrated": False,
        "replay_blocked": False,
        "orphan_detected": True,
        "stale_expired": False,
        "journal_chain_valid": False,
        "recovery_allowed": False,
    },
    "stale_expired": {
        "recovery_required": False,
        "rehydrated": False,
        "replay_blocked": False,
        "orphan_detected": False,
        "stale_expired": True,
        "journal_chain_valid": False,
        "recovery_allowed": False,
    },
    "journal_chain": {
        "recovery_required": False,
        "rehydrated": False,
        "replay_blocked": False,
        "orphan_detected": False,
        "stale_expired": False,
        "journal_chain_valid": True,
        "recovery_allowed": True,
    },
}

def fail(msg):
    raise SystemExit(f"[FAIL] {msg}")

def main():
    ap = argparse.ArgumentParser(description="Validate recovery simulator artifact.")
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

    for key, value in EXPECTED[state].items():
        if data.get(key) is not value:
            fail(f"{state}: {key} must be {value}")

    print(f"[PASS] recovery simulator valid: {path}")

if __name__ == "__main__":
    main()
