#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / "watch" / "state"

OUT = STATE / "constrained-sandbox-pilot-design.json"
HISTORY = STATE / "constrained-sandbox-pilot-design-history.jsonl"

snapshot = {
    "schema": "starfleet.constrained_sandbox_pilot_design.v1",
    "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    "mode": "read_only",
    "design_only": True,
    "advisory_only": True,
    "execution_allowed": False,
    "mutation_authority": False,
    "live_executor_enabled": False,
    "worker_self_apply_allowed": False,
    "ready_for_sandbox_live_implementation": False,
    "ready_for_live_infrastructure_mutation": False,
    "sandbox_path": "/tmp/spot-sandbox-pilot/",
    "kill_switch_path": "watch/state/executor-kill-switch.enabled",
    "backup_root": "/mnt/collective/backups/spot-sandbox-pilot/",
    "action_log_root": "/mnt/collective/logs/spot/actions/",
    "rollback_log_root": "/mnt/collective/logs/spot/rollbacks/",
    "allowed_future_actions": [
        "create_test_file_inside_sandbox",
        "write_non_sensitive_test_content",
        "verify_checksum",
        "rollback_test_file"
    ],
    "forbidden_actions": [
        "service_restart",
        "system_config_mutation",
        "firewall_mutation",
        "dns_mutation",
        "dhcp_mutation",
        "routing_mutation",
        "ssh_mutation",
        "production_path_write",
        "worker_self_apply",
        "backup_delete",
        "audit_delete",
        "execution_outside_sandbox"
    ],
    "required_future_gates": [
        "explicit_operator_approval",
        "backup_artifact_recorded",
        "rollback_plan_defined",
        "kill_switch_checked",
        "immutable_action_journal_defined",
        "deterministic_validator_present",
        "spot_core_sole_executor",
        "governance_mode_change_documented"
    ],
}

STATE.mkdir(parents=True, exist_ok=True)

tmp = str(OUT) + ".tmp"
with open(tmp, "w", encoding="utf-8") as f:
    json.dump(snapshot, f, indent=2, sort_keys=True)
    f.write("\n")

os.replace(tmp, OUT)

with open(HISTORY, "a", encoding="utf-8") as f:
    f.write(json.dumps(snapshot, sort_keys=True) + "\n")

print(json.dumps(snapshot, indent=2, sort_keys=True))
