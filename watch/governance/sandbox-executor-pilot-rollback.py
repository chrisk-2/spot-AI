#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / "watch" / "state"
SNAP = STATE / "sandbox-executor-pilot.json"
ROLLBACK_LOG = Path("/mnt/collective/logs/spot/rollbacks")

def now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()

if not SNAP.exists():
    raise SystemExit("[FAIL] sandbox pilot snapshot missing")

data = json.loads(SNAP.read_text())
target = Path(data["target"])
backup_dir = Path(data["backup_dir"])
meta = json.loads((backup_dir / "metadata.json").read_text())

if meta["pre_exists"]:
    shutil.copy2(backup_dir / target.name, target)
    action = "restored_existing_file"
else:
    if target.exists():
        target.unlink()
    action = "deleted_created_file"

record = {
    "schema": "starfleet.sandbox_executor_pilot_rollback.v1",
    "generated_at": now(),
    "target": str(target),
    "backup_dir": str(backup_dir),
    "rollback_action": action,
    "result": "PASS",
}

ROLLBACK_LOG.mkdir(parents=True, exist_ok=True)
path = ROLLBACK_LOG / f"sandbox-rollback-{datetime.now().strftime('%Y%m%dT%H%M%SZ')}.json"
path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")

print(json.dumps(record, indent=2, sort_keys=True))
