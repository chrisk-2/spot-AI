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

OUT = STATE / "governed-noop-transaction-rehearsal.json"
HISTORY = STATE / "governed-noop-transaction-history.jsonl"

LINKS = {
    "execution_state_drift": STATE / "execution-state-drift.json",
    "noop_executor_lifecycle": STATE / "noop-executor-lifecycle.json",
    "execution_reconciliation": STATE / "execution-reconciliation-journal.json",
    "lease_receipt_reconciliation": STATE / "lease-receipt-reconciliation-audit.json",
}

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


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def read_link(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"present": False, "path": str(path.relative_to(ROOT))}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
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


def event(index: int, state: str, txid: str, previous_hash: str) -> dict[str, Any]:
    payload = {
        "index": index,
        "state": state,
        "transaction_id": txid,
        "timestamp": now(),
        "simulated": True,
        "execution_performed": False,
        "mutation_performed": False,
        "previous_hash": previous_hash,
    }
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()
    payload["event_hash"] = digest
    return payload


def build() -> dict[str, Any]:
    STATE.mkdir(parents=True, exist_ok=True)

    txid = f"noop-tx-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    links = {name: read_link(path) for name, path in LINKS.items()}

    events = []
    previous_hash = "GENESIS"
    for idx, state in enumerate(CHAIN, 1):
        ev = event(idx, state, txid, previous_hash)
        events.append(ev)
        previous_hash = ev["event_hash"]

    blockers = []
    for name, link in links.items():
        if not link.get("present"):
            blockers.append(f"missing linked artifact: {name}")
        if link.get("execution_allowed") is True:
            blockers.append(f"linked artifact unexpectedly allows execution: {name}")
        if link.get("mutation_authority") is True:
            blockers.append(f"linked artifact unexpectedly grants mutation authority: {name}")
        if link.get("live_executor_enabled") is True:
            blockers.append(f"linked artifact unexpectedly enables live executor: {name}")

    snapshot = {
        "schema": "starfleet.governed_noop_transaction_rehearsal.v1",
        "generated_at": now(),
        "transaction_id": txid,
        "mode": "read_only",
        "advisory_only": True,
        "rehearsal_only": True,
        "execution_allowed": False,
        "mutation_authority": False,
        "live_executor_enabled": False,
        "worker_self_apply_allowed": False,
        "spot_core_remains_sole_executor": True,
        "chain": CHAIN,
        "events": events,
        "event_count": len(events),
        "closed": events[-1]["state"] == "TRANSACTION_CLOSED",
        "final_event_hash": events[-1]["event_hash"],
        "linked_artifacts": links,
        "blockers": blockers,
        "rehearsal_passed": len(blockers) == 0,
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
