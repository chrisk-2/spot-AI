#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT_PATH = ROOT / "watch" / "state" / "noop-executor-lifecycle.json"
HISTORY_PATH = ROOT / "watch" / "state" / "noop-executor-lifecycle-history.jsonl"

ORDERED_STATES = [
    "EXECUTOR_CREATED",
    "EXECUTOR_READY",
    "EXECUTOR_LEASE_BOUND",
    "EXECUTOR_RECEIPT_BOUND",
    "EXECUTOR_APPROVAL_VERIFIED",
    "EXECUTOR_NOOP_DISPATCH",
    "EXECUTOR_NOOP_COMPLETE",
    "EXECUTOR_CLOSED",
]


def fail(msg: str) -> int:
    print(f"[FAIL] {msg}")
    return 1


def ok(msg: str) -> None:
    print(f"[PASS] {msg}")


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def validate_snapshot(snapshot: dict[str, Any]) -> int:
    if snapshot.get("schema") != "starfleet.noop_executor_lifecycle.v1":
        return fail("snapshot schema mismatch")
    ok("snapshot schema valid")

    required_false = [
        "execution_allowed",
        "mutation_authority",
        "live_executor_enabled",
        "worker_self_apply_allowed",
    ]
    for key in required_false:
        if snapshot.get(key) is not False:
            return fail(f"{key} must remain false")
        ok(f"{key} false")

    required_true = [
        "simulation_only",
        "advisory_only",
        "spot_core_remains_sole_executor",
        "closed",
    ]
    for key in required_true:
        if snapshot.get(key) is not True:
            return fail(f"{key} must remain true")
        ok(f"{key} true")

    if snapshot.get("mode") != "read_only":
        return fail("mode must remain read_only")
    ok("mode read_only")

    if snapshot.get("ordered_states") != ORDERED_STATES:
        return fail("ordered_states mismatch")
    ok("ordered states valid")

    events = snapshot.get("events")
    if not isinstance(events, list):
        return fail("events must be a list")
    if len(events) != len(ORDERED_STATES):
        return fail("event count mismatch")

    actual = []
    for idx, event in enumerate(events, 1):
        if not isinstance(event, dict):
            return fail(f"event[{idx}] is not an object")
        if event.get("index") != idx:
            return fail(f"event[{idx}] index mismatch")
        if event.get("mutation_performed") is not False:
            return fail(f"event[{idx}] mutation_performed must be false")
        if event.get("execution_performed") is not False:
            return fail(f"event[{idx}] execution_performed must be false")
        if event.get("simulated") is not True:
            return fail(f"event[{idx}] simulated must be true")
        actual.append(event.get("state"))

    if actual != ORDERED_STATES:
        return fail("event lifecycle ordering mismatch")
    ok("event lifecycle ordering valid")

    link = snapshot.get("linked_execution_state_drift")
    if not isinstance(link, dict):
        return fail("linked_execution_state_drift must be an object")
    if link.get("present") is True:
        if link.get("execution_allowed") is not False:
            return fail("linked drift execution_allowed must be false")
        if link.get("mutation_authority") is not False:
            return fail("linked drift mutation_authority must be false")
        ok("linked drift governance remains non-mutating")
    else:
        ok("linked drift snapshot absent; lifecycle remains standalone read-only")

    return 0


def validate_history() -> int:
    if not HISTORY_PATH.exists():
        return fail("noop executor lifecycle history missing")

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
            if not isinstance(record, dict):
                return fail(f"history line {lineno} is not an object")
            if record.get("schema") != "starfleet.noop_executor_lifecycle.v1":
                return fail(f"history line {lineno} invalid schema")
            count += 1

    if count < 1:
        return fail("noop executor lifecycle history empty")

    ok(f"history JSONL valid count={count}")
    return 0


def main() -> int:
    if not SNAPSHOT_PATH.exists():
        return fail("noop executor lifecycle snapshot missing")

    try:
        snapshot = load_json(SNAPSHOT_PATH)
    except Exception as exc:
        return fail(f"snapshot invalid JSON: {exc}")

    if not isinstance(snapshot, dict):
        return fail("snapshot must be an object")
    ok("snapshot valid JSON")

    if validate_snapshot(snapshot) != 0:
        return 1

    if validate_history() != 0:
        return 1

    print("RESULT: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
