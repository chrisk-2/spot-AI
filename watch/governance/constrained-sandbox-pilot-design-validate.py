#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / "watch" / "state"

SNAP = STATE / "constrained-sandbox-pilot-design.json"
HISTORY = STATE / "constrained-sandbox-pilot-design-history.jsonl"

def fail(msg):
    print(f"[FAIL] {msg}")
    raise SystemExit(1)

def ok(msg):
    print(f"[PASS] {msg}")

data = json.loads(SNAP.read_text())

if data["schema"] != "starfleet.constrained_sandbox_pilot_design.v1":
    fail("schema mismatch")
ok("schema valid")

for key in (
    "execution_allowed",
    "mutation_authority",
    "live_executor_enabled",
    "worker_self_apply_allowed",
    "ready_for_sandbox_live_implementation",
    "ready_for_live_infrastructure_mutation",
):
    if data[key] is not False:
        fail(f"{key} must be false")
    ok(f"{key} false")

for key in ("design_only", "advisory_only"):
    if data[key] is not True:
        fail(f"{key} must be true")
    ok(f"{key} true")

if data["mode"] != "read_only":
    fail("mode mismatch")
ok("mode read_only")

if data["sandbox_path"] != "/tmp/spot-sandbox-pilot/":
    fail("sandbox path mismatch")
ok("sandbox path constrained")

for forbidden in (
    "firewall_mutation",
    "dns_mutation",
    "routing_mutation",
    "service_restart",
    "production_path_write",
    "execution_outside_sandbox",
):
    if forbidden not in data["forbidden_actions"]:
        fail(f"missing forbidden action: {forbidden}")
ok("forbidden actions present")

for gate in (
    "explicit_operator_approval",
    "backup_artifact_recorded",
    "rollback_plan_defined",
    "kill_switch_checked",
    "spot_core_sole_executor",
):
    if gate not in data["required_future_gates"]:
        fail(f"missing required gate: {gate}")
ok("required future gates present")

count = len([x for x in HISTORY.read_text().splitlines() if x.strip()])
ok(f"history count={count}")

print("RESULT: PASS")
