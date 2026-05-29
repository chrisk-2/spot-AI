#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / "watch" / "state"

SNAP = STATE / "deterministic-noop-execution-replay.json"
HISTORY = STATE / "deterministic-noop-execution-replay-history.jsonl"

def fail(msg):
    print(f"[FAIL] {msg}")
    raise SystemExit(1)

def ok(msg):
    print(f"[PASS] {msg}")

data = json.loads(SNAP.read_text())

if data["schema"] != "starfleet.deterministic_noop_execution_replay.v1":
    fail("schema mismatch")
ok("schema valid")

for key in (
    "execution_allowed",
    "mutation_authority",
    "live_executor_enabled",
    "worker_self_apply_allowed",
):
    if data[key] is not False:
        fail(f"{key} must be false")
    ok(f"{key} false")

for key in (
    "advisory_only",
    "replay_only",
):
    if data[key] is not True:
        fail(f"{key} must be true")
    ok(f"{key} true")

if data["mode"] != "read_only":
    fail("mode mismatch")
ok("mode read_only")

if data["source_present"] is not True:
    fail("source missing")
ok("source present")

if data["source_rehearsal_passed"] is not True:
    fail("source rehearsal failed")
ok("source rehearsal passed")

if data["replay_passed"] is not True:
    fail("replay failed")
ok("replay passed")

if data["blockers"]:
    fail("blockers present")
ok("blockers clear")

if not isinstance(data["replay_digest"], str):
    fail("replay digest invalid")
ok("replay digest valid")

count = len(
    [x for x in HISTORY.read_text().splitlines() if x.strip()]
)
ok(f"history count={count}")

print("RESULT: PASS")
