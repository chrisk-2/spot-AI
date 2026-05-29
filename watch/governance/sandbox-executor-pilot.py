#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / "watch" / "state"

SANDBOX = Path("/tmp/spot-sandbox-pilot")
TARGET = SANDBOX / "spot-sandbox-test.txt"
KILL = STATE / "executor-kill-switch.enabled"

BACKUP_ROOT = Path("/mnt/collective/backups/spot-sandbox-pilot")
ACTION_LOG = Path("/mnt/collective/logs/spot/actions")
ROLLBACK_LOG = Path("/mnt/collective/logs/spot/rollbacks")

OUT = STATE / "sandbox-executor-pilot.json"
HISTORY = STATE / "sandbox-executor-pilot-history.jsonl"

def now():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()

def sha(path: Path):
    if not path.exists():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()

def write_json(path: Path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = str(path) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, sort_keys=True)
        f.write("\n")
    os.replace(tmp, path)

if os.environ.get("SPOT_SANDBOX_APPROVED") != "YES":
    raise SystemExit("[FAIL] SPOT_SANDBOX_APPROVED=YES required")

if KILL.exists():
    raise SystemExit("[FAIL] executor kill switch enabled")

SANDBOX.mkdir(parents=True, exist_ok=True)
BACKUP_ROOT.mkdir(parents=True, exist_ok=True)
ACTION_LOG.mkdir(parents=True, exist_ok=True)
ROLLBACK_LOG.mkdir(parents=True, exist_ok=True)

stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
backup_dir = BACKUP_ROOT / stamp
backup_dir.mkdir(parents=True, exist_ok=False)

pre_exists = TARGET.exists()
pre_sha = sha(TARGET)

if pre_exists:
    shutil.copy2(TARGET, backup_dir / TARGET.name)

rollback_plan = {
    "target": str(TARGET),
    "pre_exists": pre_exists,
    "pre_sha256": pre_sha,
    "backup_dir": str(backup_dir),
    "rollback_action": "restore_existing_file" if pre_exists else "delete_created_file",
}
write_json(backup_dir / "metadata.json", rollback_plan)

content = f"spot sandbox pilot\ncreated_at={now()}\n"
TARGET.write_text(content, encoding="utf-8")
post_sha = sha(TARGET)

action = {
    "schema": "starfleet.sandbox_executor_pilot.v1",
    "generated_at": now(),
    "mode": "sandbox_live_only",
    "sandbox_path": str(SANDBOX),
    "target": str(TARGET),
    "backup_dir": str(backup_dir),
    "execution_allowed": True,
    "live_infrastructure_mutation": False,
    "mutation_authority": False,
    "worker_self_apply_allowed": False,
    "action": "create_or_update_test_file",
    "pre_exists": pre_exists,
    "pre_sha256": pre_sha,
    "post_sha256": post_sha,
    "rollback_plan_defined": True,
    "kill_switch_checked": True,
    "operator_approval": "SPOT_SANDBOX_APPROVED=YES",
    "result": "PASS",
}

write_json(ACTION_LOG / f"sandbox-action-{stamp}.json", action)
write_json(OUT, action)

with HISTORY.open("a", encoding="utf-8") as f:
    f.write(json.dumps(action, sort_keys=True) + "\n")

print(json.dumps(action, indent=2, sort_keys=True))
