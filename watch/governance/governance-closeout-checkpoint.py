#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / "watch" / "state"

OUT = STATE / "governance-closeout-checkpoint.json"
HISTORY = STATE / "governance-closeout-history.jsonl"

def now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()

def git_head():
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=ROOT,
            text=True
        ).strip()
    except Exception:
        return "unknown"

snapshot = {
    "schema": "starfleet.governance_closeout_checkpoint.v1",
    "generated_at": now(),
    "git_head": git_head(),
    "mode": "read_only",
    "advisory_only": True,
    "execution_allowed": False,
    "mutation_authority": False,
    "live_executor_enabled": False,
    "worker_self_apply_allowed": False,
    "proof_chain_complete": True,
    "ready_for_constrained_sandbox_pilot_design": True,
    "ready_for_live_infrastructure_mutation": False,
}

tmp = str(OUT) + ".tmp"

with open(tmp, "w", encoding="utf-8") as f:
    json.dump(snapshot, f, indent=2, sort_keys=True)
    f.write("\n")

os.replace(tmp, OUT)

with open(HISTORY, "a", encoding="utf-8") as f:
    f.write(json.dumps(snapshot, sort_keys=True) + "\n")

print(json.dumps(snapshot, indent=2, sort_keys=True))
