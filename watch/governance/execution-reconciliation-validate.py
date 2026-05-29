#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / "watch" / "state"

SNAP = STATE / "execution-reconciliation-journal.json"
HISTORY = STATE / "execution-reconciliation-history.jsonl"

def fail(msg):
    print(f"[FAIL] {msg}")
    raise SystemExit(1)

def ok(msg):
    print(f"[PASS] {msg}")

data = json.loads(SNAP.read_text())

if data["schema"] != "starfleet.execution_reconciliation.v1":
    fail("schema mismatch")
ok("schema valid")

for key in ("execution_allowed", "mutation_authority"):
    if data[key] is not False:
        fail(f"{key} must be false")
    ok(f"{key} false")

if data["mode"] != "read_only":
    fail("mode mismatch")
ok("mode read_only")

if data["advisory_only"] is not True:
    fail("advisory_only mismatch")
ok("advisory_only true")

if not HISTORY.exists():
    fail("history missing")

count = len([x for x in HISTORY.read_text().splitlines() if x.strip()])
ok(f"history count={count}")

print("RESULT: PASS")
