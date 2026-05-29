#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / "watch" / "state"

OUT = STATE / "noop-governance-readiness-gate.json"
HISTORY = STATE / "noop-governance-readiness-history.jsonl"

REQUIRED = {
    "execution_state_drift": STATE / "execution-state-drift.json",
    "noop_executor_lifecycle": STATE / "noop-executor-lifecycle.json",
    "execution_reconciliation": STATE / "execution-reconciliation-journal.json",
    "lease_receipt_reconciliation": STATE / "lease-receipt-reconciliation-audit.json",
    "governed_noop_transaction": STATE / "governed-noop-transaction-rehearsal.json",
    "deterministic_noop_replay": STATE / "deterministic-noop-execution-replay.json",
}

def now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()

def inspect(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"present": False, "path": str(path.relative_to(ROOT))}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return {"present": False, "path": str(path.relative_to(ROOT)), "error": str(exc)}
    return {
        "present": True,
        "path": str(path.relative_to(ROOT)),
        "schema": data.get("schema"),
        "generated_at": data.get("generated_at"),
        "mode": data.get("mode"),
        "advisory_only": data.get("advisory_only"),
        "execution_allowed": data.get("execution_allowed"),
        "mutation_authority": data.get("mutation_authority"),
        "live_executor_enabled": data.get("live_executor_enabled"),
        "worker_self_apply_allowed": data.get("worker_self_apply_allowed"),
        "passed": data.get("replay_passed", data.get("rehearsal_passed", data.get("closed", True))),
    }

def main():
    STATE.mkdir(parents=True, exist_ok=True)
    artifacts = {name: inspect(path) for name, path in REQUIRED.items()}
    blockers = []

    for name, item in artifacts.items():
        if item.get("present") is not True:
            blockers.append(f"missing artifact: {name}")
        if item.get("execution_allowed") is True:
            blockers.append(f"execution allowed in {name}")
        if item.get("mutation_authority") is True:
            blockers.append(f"mutation authority in {name}")
        if item.get("live_executor_enabled") is True:
            blockers.append(f"live executor enabled in {name}")
        if item.get("worker_self_apply_allowed") is True:
            blockers.append(f"worker self-apply allowed in {name}")
        if item.get("mode") not in (None, "read_only"):
            blockers.append(f"non-read-only mode in {name}")

    snapshot = {
        "schema": "starfleet.noop_governance_readiness_gate.v1",
        "generated_at": now(),
        "mode": "read_only",
        "advisory_only": True,
        "readiness_gate_only": True,
        "execution_allowed": False,
        "mutation_authority": False,
        "live_executor_enabled": False,
        "worker_self_apply_allowed": False,
        "required_artifacts": artifacts,
        "blockers": blockers,
        "ready_for_constrained_sandbox_pilot_design": len(blockers) == 0,
        "ready_for_live_infrastructure_mutation": False,
    }

    tmp = OUT.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, OUT)

    with HISTORY.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(snapshot, sort_keys=True) + "\n")

    print(json.dumps(snapshot, indent=2, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
