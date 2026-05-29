#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / "watch" / "state"

SNAP = STATE / "governed-noop-transaction-rehearsal.json"
HISTORY = STATE / "governed-noop-transaction-history.jsonl"

CHAIN = [
    "INTENT_RECEIVED",
    "RISK_CLASSIFIED",
    "APPROVAL_MODELED",
    "LEASE_MODELED",
    "RECEIPT_MODELED",
    "ROLLBACK_BINDING_MODELED",
    "RECONCILIATION_MODELED",
    "REPLAY_AUDIT_MODELED",
    "NOOP_LIFECYCLE_MODELED",
    "TRANSACTION_CLOSED",
]


def fail(msg: str) -> int:
    print(f"[FAIL] {msg}")
    return 1


def ok(msg: str) -> None:
    print(f"[PASS] {msg}")


def load(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def main() -> int:
    if not SNAP.exists():
        return fail("governed noop transaction snapshot missing")

    try:
        data = load(SNAP)
    except Exception as exc:
        return fail(f"snapshot invalid JSON: {exc}")

    if not isinstance(data, dict):
        return fail("snapshot must be object")
    ok("snapshot valid JSON")

    if data.get("schema") != "starfleet.governed_noop_transaction_rehearsal.v1":
        return fail("schema mismatch")
    ok("schema valid")

    for key in ("execution_allowed", "mutation_authority", "live_executor_enabled", "worker_self_apply_allowed"):
        if data.get(key) is not False:
            return fail(f"{key} must be false")
        ok(f"{key} false")

    for key in ("advisory_only", "rehearsal_only", "spot_core_remains_sole_executor", "closed"):
        if data.get(key) is not True:
            return fail(f"{key} must be true")
        ok(f"{key} true")

    if data.get("mode") != "read_only":
        return fail("mode must be read_only")
    ok("mode read_only")

    if data.get("chain") != CHAIN:
        return fail("chain mismatch")
    ok("chain valid")

    events = data.get("events")
    if not isinstance(events, list) or len(events) != len(CHAIN):
        return fail("events invalid")

    previous = "GENESIS"
    actual_chain = []
    for idx, ev in enumerate(events, 1):
        if not isinstance(ev, dict):
            return fail(f"event[{idx}] must be object")
        if ev.get("index") != idx:
            return fail(f"event[{idx}] index mismatch")
        if ev.get("previous_hash") != previous:
            return fail(f"event[{idx}] previous_hash mismatch")
        if ev.get("simulated") is not True:
            return fail(f"event[{idx}] simulated must be true")
        if ev.get("execution_performed") is not False:
            return fail(f"event[{idx}] execution_performed must be false")
        if ev.get("mutation_performed") is not False:
            return fail(f"event[{idx}] mutation_performed must be false")
        event_hash = ev.get("event_hash")
        if not isinstance(event_hash, str) or len(event_hash) != 64:
            return fail(f"event[{idx}] event_hash invalid")
        previous = event_hash
        actual_chain.append(ev.get("state"))

    if actual_chain != CHAIN:
        return fail("event chain order mismatch")
    ok("event chain order valid")
    ok("event hash chain valid")

    blockers = data.get("blockers")
    if not isinstance(blockers, list):
        return fail("blockers must be list")

    if blockers:
        return fail("rehearsal has blockers: " + "; ".join(str(x) for x in blockers))
    ok("rehearsal blockers clear")

    if data.get("rehearsal_passed") is not True:
        return fail("rehearsal_passed must be true")
    ok("rehearsal passed")

    links = data.get("linked_artifacts")
    if not isinstance(links, dict):
        return fail("linked_artifacts must be object")

    required_links = {
        "execution_state_drift",
        "noop_executor_lifecycle",
        "execution_reconciliation",
        "lease_receipt_reconciliation",
    }

    for name in required_links:
        link = links.get(name)
        if not isinstance(link, dict):
            return fail(f"linked artifact missing: {name}")
        if link.get("present") is not True:
            return fail(f"linked artifact not present: {name}")
        if link.get("execution_allowed") is True:
            return fail(f"linked artifact allows execution: {name}")
        if link.get("mutation_authority") is True:
            return fail(f"linked artifact grants mutation authority: {name}")

    ok("linked artifacts present and non-mutating")

    if not HISTORY.exists():
        return fail("history missing")

    count = 0
    with HISTORY.open("r", encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except Exception as exc:
                return fail(f"history line {lineno} invalid JSON: {exc}")
            if rec.get("schema") != "starfleet.governed_noop_transaction_rehearsal.v1":
                return fail(f"history line {lineno} schema mismatch")
            count += 1

    if count < 1:
        return fail("history empty")

    ok(f"history JSONL valid count={count}")
    print("RESULT: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
