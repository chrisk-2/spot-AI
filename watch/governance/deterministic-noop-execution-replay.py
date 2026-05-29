#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / "watch" / "state"

SOURCE = STATE / "governed-noop-transaction-rehearsal.json"
OUT = STATE / "deterministic-noop-execution-replay.json"
HISTORY = STATE / "deterministic-noop-execution-replay-history.jsonl"

CONTEXT = {
    "lease_receipt_reconciliation": STATE / "lease-receipt-reconciliation-audit.json",
    "execution_reconciliation": STATE / "execution-reconciliation-journal.json",
    "noop_executor_lifecycle": STATE / "noop-executor-lifecycle.json",
    "execution_state_drift": STATE / "execution-state-drift.json",
}


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def context_summary(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"present": False, "path": str(path.relative_to(ROOT))}
    try:
        data = load(path)
        return {
            "present": True,
            "path": str(path.relative_to(ROOT)),
            "schema": data.get("schema") if isinstance(data, dict) else None,
            "generated_at": data.get("generated_at") if isinstance(data, dict) else None,
            "execution_allowed": data.get("execution_allowed") if isinstance(data, dict) else None,
            "mutation_authority": data.get("mutation_authority") if isinstance(data, dict) else None,
            "live_executor_enabled": data.get("live_executor_enabled") if isinstance(data, dict) else None,
        }
    except Exception as exc:
        return {
            "present": False,
            "path": str(path.relative_to(ROOT)),
            "error": f"{type(exc).__name__}: {exc}",
        }


def canonical_event(event: dict[str, Any]) -> dict[str, Any]:
    return {
        "event_hash": event.get("event_hash"),
        "execution_performed": event.get("execution_performed"),
        "index": event.get("index"),
        "mutation_performed": event.get("mutation_performed"),
        "previous_hash": event.get("previous_hash"),
        "simulated": event.get("simulated"),
        "state": event.get("state"),
        "transaction_id": event.get("transaction_id"),
    }


def digest(obj: Any) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True).encode("utf-8")).hexdigest()


def build() -> dict[str, Any]:
    STATE.mkdir(parents=True, exist_ok=True)

    blockers: list[str] = []

    if not SOURCE.exists():
        source: dict[str, Any] = {}
        blockers.append("missing governed noop transaction rehearsal")
    else:
        data = load(SOURCE)
        source = data if isinstance(data, dict) else {}
        if not isinstance(data, dict):
            blockers.append("source rehearsal is not an object")

    source_events = source.get("events", [])
    if not isinstance(source_events, list):
        source_events = []
        blockers.append("source events invalid")

    replay_events = [canonical_event(x) for x in source_events if isinstance(x, dict)]

    if source.get("rehearsal_passed") is not True:
        blockers.append("source rehearsal did not pass")

    if source.get("execution_allowed") is not False:
        blockers.append("source execution_allowed not false")

    if source.get("mutation_authority") is not False:
        blockers.append("source mutation_authority not false")

    if source.get("live_executor_enabled") is not False:
        blockers.append("source live_executor_enabled not false")

    final_hash = source.get("final_event_hash")
    if replay_events and replay_events[-1].get("event_hash") != final_hash:
        blockers.append("source final hash does not match final replay event")

    previous = "GENESIS"
    for idx, event in enumerate(replay_events, 1):
        if event.get("index") != idx:
            blockers.append(f"event index mismatch at {idx}")
        if event.get("previous_hash") != previous:
            blockers.append(f"previous hash mismatch at {idx}")
        if event.get("execution_performed") is not False:
            blockers.append(f"execution flag mismatch at {idx}")
        if event.get("mutation_performed") is not False:
            blockers.append(f"mutation flag mismatch at {idx}")
        if event.get("simulated") is not True:
            blockers.append(f"simulated flag mismatch at {idx}")
        previous = event.get("event_hash")

    context = {name: context_summary(path) for name, path in CONTEXT.items()}

    for name, item in context.items():
        if not item.get("present"):
            blockers.append(f"context missing: {name}")
        if item.get("execution_allowed") is True:
            blockers.append(f"context allows execution: {name}")
        if item.get("mutation_authority") is True:
            blockers.append(f"context grants mutation authority: {name}")
        if item.get("live_executor_enabled") is True:
            blockers.append(f"context enables live executor: {name}")

    replay_payload = {
        "source_transaction_id": source.get("transaction_id"),
        "source_final_event_hash": final_hash,
        "source_chain": source.get("chain"),
        "replay_events": replay_events,
    }

    snapshot = {
        "schema": "starfleet.deterministic_noop_execution_replay.v1",
        "generated_at": now(),
        "mode": "read_only",
        "advisory_only": True,
        "replay_only": True,
        "execution_allowed": False,
        "mutation_authority": False,
        "live_executor_enabled": False,
        "worker_self_apply_allowed": False,
        "source_present": SOURCE.exists(),
        "source_schema": source.get("schema"),
        "source_transaction_id": source.get("transaction_id"),
        "source_rehearsal_passed": source.get("rehearsal_passed"),
        "source_final_event_hash": final_hash,
        "replay_event_count": len(replay_events),
        "replay_digest": digest(replay_payload),
        "context": context,
        "blockers": blockers,
        "replay_passed": len(blockers) == 0,
    }

    return snapshot


def main() -> int:
    snapshot = build()

    tmp = OUT.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, OUT)

    with HISTORY.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(snapshot, sort_keys=True) + "\n")

    print(json.dumps(snapshot, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
