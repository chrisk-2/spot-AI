#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / "watch" / "state"

OUT = STATE / "execution-reconciliation-journal.json"
HISTORY = STATE / "execution-reconciliation-history.jsonl"

LINKS = {
    "execution_state_drift": STATE / "execution-state-drift.json",
    "noop_executor_lifecycle": STATE / "noop-executor-lifecycle.json",
}

def load(path):
    if not path.exists():
        return {"present": False}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return {
            "present": True,
            "schema": data.get("schema"),
            "generated_at": data.get("generated_at"),
        }
    except Exception as exc:
        return {
            "present": False,
            "error": str(exc),
        }

snapshot = {
    "schema": "starfleet.execution_reconciliation.v1",
    "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    "mode": "read_only",
    "advisory_only": True,
    "execution_allowed": False,
    "mutation_authority": False,
    "reconciliation_complete": True,
    "artifacts": {k: load(v) for k, v in LINKS.items()},
}

tmp = str(OUT) + ".tmp"

with open(tmp, "w", encoding="utf-8") as f:
    json.dump(snapshot, f, indent=2, sort_keys=True)
    f.write("\n")

os.replace(tmp, OUT)

with open(HISTORY, "a", encoding="utf-8") as f:
    f.write(json.dumps(snapshot, sort_keys=True) + "\n")

print(json.dumps(snapshot, indent=2, sort_keys=True))
