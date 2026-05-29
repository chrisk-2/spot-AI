#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / "watch" / "state"

SNAP = STATE / "noop-governance-readiness-gate.json"
HISTORY = STATE / "noop-governance-readiness-history.jsonl"

def fail(msg):
    print(f"[FAIL] {msg}")
    raise SystemExit(1)

def ok(msg):
    print(f"[PASS] {msg}")

data = json.loads(SNAP.read_text())

if data["schema"] != "starfleet.noop_governance_readiness_gate.v1":
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
    "readiness_gate_only",
    "ready_for_constrained_sandbox_pilot_design",
):
    if data[key] is not True:
        fail(f"{key} must be true")
    ok(f"{key} true")

if data["mode"] != "read_only":
    fail("mode mismatch")
ok("mode read_only")

if data["blockers"]:
    fail("blockers present")
ok("blockers clear")

artifacts = data["required_artifacts"]
for name, item in artifacts.items():
    if item["present"] is not True:
        fail(f"{name} missing")
    if item.get("execution_allowed") is True:
        fail(f"{name} allows execution")
    if item.get("mutation_authority") is True:
        fail(f"{name} grants mutation authority")
    if item.get("live_executor_enabled") is True:
        fail(f"{name} enables live executor")
ok("required artifacts present and non-mutating")

count = len([x for x in HISTORY.read_text().splitlines() if x.strip()])
ok(f"history count={count}")

print("RESULT: PASS")
