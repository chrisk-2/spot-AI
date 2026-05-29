#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
STATE_DIR = ROOT / "watch" / "state"
SNAPSHOT_PATH = STATE_DIR / "noop-executor-lifecycle.json"
HISTORY_PATH = STATE_DIR / "noop-executor-lifecycle-history.jsonl"
DRIFT_PATH = STATE_DIR / "execution-state-drift.json"

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


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_optional_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as fh:
        data = json.load(fh)
    return data if isinstance(data, dict) else None


def make_event(idx: int, state: str, run_id: str) -> dict[str, Any]:
    return {
        "index": idx,
        "state": state,
        "run_id": run_id,
        "simulated": True,
        "mutation_performed": False,
        "execution_performed": False,
        "timestamp": utc_now(),
    }


def build_snapshot() -> dict[str, Any]:
    STATE_DIR.mkdir(parents=True, exist_ok=True)

    run_id = f"noop-executor-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}"
    drift = load_optional_json(DRIFT_PATH)

    events = [make_event(idx, state, run_id) for idx, state in enumerate(ORDERED_STATES, 1)]

    snapshot = {
        "schema": "starfleet.noop_executor_lifecycle.v1",
        "generated_at": utc_now(),
        "run_id": run_id,
        "mode": "read_only",
        "simulation_only": True,
        "advisory_only": True,
        "execution_allowed": False,
        "mutation_authority": False,
        "live_executor_enabled": False,
        "spot_core_remains_sole_executor": True,
        "worker_self_apply_allowed": False,
        "ordered_states": ORDERED_STATES,
        "events": events,
        "closed": events[-1]["state"] == "EXECUTOR_CLOSED",
        "linked_execution_state_drift": {
            "present": drift is not None,
            "schema": drift.get("schema") if drift else None,
            "generated_at": drift.get("generated_at") if drift else None,
            "drift_count": drift.get("drift_count") if drift else None,
            "mode": drift.get("mode") if drift else None,
            "execution_allowed": drift.get("execution_allowed") if drift else None,
            "mutation_authority": drift.get("mutation_authority") if drift else None,
        },
    }

    return snapshot


def main() -> int:
    snapshot = build_snapshot()

    tmp = SNAPSHOT_PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, SNAPSHOT_PATH)

    with HISTORY_PATH.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(snapshot, sort_keys=True) + "\n")

    print(json.dumps(snapshot, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
