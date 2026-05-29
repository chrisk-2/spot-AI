#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / "watch" / "state"
SNAP = STATE / "sandbox-executor-pilot.json"

def fail(msg):
    print(f"[FAIL] {msg}")
    raise SystemExit(1)

def ok(msg):
    print(f"[PASS] {msg}")

data = json.loads(SNAP.read_text())

if data["schema"] != "starfleet.sandbox_executor_pilot.v1":
    fail("schema mismatch")
ok("schema valid")

if data["live_infrastructure_mutation"] is not False:
    fail("live infrastructure mutation must be false")
ok("live infrastructure mutation false")

if data["mutation_authority"] is not False:
    fail("mutation authority must remain false")
ok("mutation authority false")

if data["worker_self_apply_allowed"] is not False:
    fail("worker self apply must remain false")
ok("worker self apply false")

if not data["target"].startswith("/tmp/spot-sandbox-pilot/"):
    fail("target outside sandbox")
ok("target constrained to sandbox")

if not Path(data["backup_dir"]).exists():
    fail("backup dir missing")
ok("backup dir exists")

if data["result"] != "PASS":
    fail("sandbox action failed")
ok("sandbox action pass")

print("RESULT: PASS")
