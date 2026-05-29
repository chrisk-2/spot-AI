#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT_PATH = ROOT / "watch" / "state" / "execution-state-drift.json"
HISTORY_PATH = ROOT / "watch" / "state" / "execution-state-drift-history.jsonl"

KNOWN = {
    "NONE",
    "LEASE_MISSING",
    "LEASE_WITHOUT_RECEIPT",
    "RECEIPT_WITHOUT_LEASE",
    "ROLLBACK_BINDING_MISSING",
    "RECONCILIATION_MISMATCH",
    "REPLAY_AUDIT_MISSING",
    "APPROVAL_STATE_MISMATCH",
    "GOVERNANCE_STATE_MISMATCH",
}


def fail(msg: str) -> int:
    print(f"[FAIL] {msg}")
    return 1


def ok(msg: str) -> None:
    print(f"[PASS] {msg}")


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def validate_history() -> int:
    if not HISTORY_PATH.exists():
        return fail("execution state drift history missing")

    count = 0
    with HISTORY_PATH.open("r", encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except Exception as exc:
                return fail(f"history line {lineno} invalid JSON: {exc}")
            if record.get("schema") != "starfleet.execution_state_drift.v1":
                return fail(f"history line {lineno} invalid schema")
            count += 1

    if count < 1:
        return fail("execution state drift history empty")

    ok(f"history JSONL valid count={count}")
    return 0


def main() -> int:
    if not SNAPSHOT_PATH.exists():
        return fail("execution state drift snapshot missing")

    try:
        snapshot = load_json(SNAPSHOT_PATH)
    except Exception as exc:
        return fail(f"snapshot invalid JSON: {exc}")

    ok("snapshot valid JSON")

    if snapshot.get("schema") != "starfleet.execution_state_drift.v1":
        return fail("snapshot schema mismatch")
    ok("snapshot schema valid")

    if snapshot.get("mode") != "read_only":
        return fail("governance mode is not read_only")
    ok("governance mode read_only")

    if snapshot.get("execution_allowed") is not False:
        return fail("execution_allowed must remain false")
    ok("execution_allowed false")

    if snapshot.get("mutation_authority") is not False:
        return fail("mutation_authority must remain false")
    ok("mutation_authority false")

    if snapshot.get("advisory_only") is not True:
        return fail("advisory_only must remain true")
    ok("advisory_only true")

    drifts = snapshot.get("drifts")
    if not isinstance(drifts, list) or not drifts:
        return fail("drifts must be a non-empty list")

    for idx, drift in enumerate(drifts):
        if not isinstance(drift, dict):
            return fail(f"drift[{idx}] is not an object")
        classification = drift.get("classification")
        if classification not in KNOWN:
            return fail(f"drift[{idx}] has unknown classification: {classification}")

    ok("all drift classifications known")

    if validate_history() != 0:
        return 1

    print("RESULT: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
