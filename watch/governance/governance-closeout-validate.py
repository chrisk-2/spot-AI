#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / "watch" / "state"

SNAP = STATE / "governance-closeout-checkpoint.json"
HISTORY = STATE / "governance-closeout-history.jsonl"

def fail(msg):
    print(f"[FAIL] {msg}")
    raise SystemExit(1)

def ok(msg):
    print(f"[PASS] {msg}")

data = json.loads(SNAP.read_text())

if data["schema"] != "starfleet.governance_closeout_checkpoint.v1":
    fail("schema mismatch")
ok("schema valid")

for key in (
    "execution_allowed",
    "mutation_authority",
    "live_executor_enabled",
    "worker_self_apply_allowed",
    "ready_for_live_infrastructure_mutation",
):
    if data[key] is not False:
        fail(f"{key} must be false")
    ok(f"{key} false")

for key in (
    "advisory_only",
    "proof_chain_complete",
    "ready_for_constrained_sandbox_pilot_design",
):
    if data[key] is not True:
        fail(f"{key} must be true")
    ok(f"{key} true")

ok("closeout checkpoint valid")
print("RESULT: PASS")
