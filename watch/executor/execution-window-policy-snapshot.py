#!/usr/bin/env python3
import json
from datetime import datetime, timezone

data = {
    "module": "governed_execution_window_policy",
    "mode": "read_only",
    "advisory_only": True,
    "execution_allowed": False,
    "mutation_authority": False,
    "executor": "spot-core",
    "window_schema": {
        "window_id_required": True,
        "request_id_required": True,
        "action_id_required": True,
        "executor_required": True,
        "target_required": True,
        "service_required": True,
        "risk_class_required": True,
        "allowed_start_required": True,
        "allowed_end_required": True,
        "timezone_required": True,
        "approval_required_field_required": True,
        "emergency_override_policy_required": True,
        "journal_path_required": True
    },
    "window_rules": {
        "missing_window_blocks_execution": True,
        "expired_window_blocks_execution": True,
        "early_execution_blocks_execution": True,
        "high_risk_windows_require_approval": True,
        "emergency_override_requires_journal_entry": True,
        "window_does_not_authorize_execution": True,
        "spot_core_required_for_enforcement": True
    },
    "generated_at": datetime.now(timezone.utc).isoformat()
}

print(json.dumps(data, indent=2, sort_keys=True))
