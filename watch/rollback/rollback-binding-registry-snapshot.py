#!/usr/bin/env python3
import json
from datetime import datetime, timezone

data = {
    "module": "rollback_binding_registry",
    "mode": "read_only",
    "advisory_only": True,
    "execution_allowed": False,
    "mutation_authority": False,
    "executor": "spot-core",
    "rollback_binding_schema": {
        "rollback_binding_id_required": True,
        "request_id_required": True,
        "action_id_required": True,
        "target_required": True,
        "service_required": True,
        "risk_class_required": True,
        "backup_binding_id_required": True,
        "rollback_strategy_required": True,
        "rollback_procedure_reference_required": True,
        "rollback_validation_command_required": True,
        "rollback_halt_condition_required": True,
        "journal_path_required": True,
        "timestamp_required": True
    },
    "binding_rules": {
        "rollback_binding_required_before_execution": True,
        "backup_binding_required_before_rollback_binding": True,
        "rollback_binding_does_not_authorize_execution": True,
        "rollback_execution_requires_spot_core": True,
        "rollback_journal_required": True,
        "rollback_delete_forbidden": True
    },
    "generated_at": datetime.now(timezone.utc).isoformat()
}

print(json.dumps(data, indent=2, sort_keys=True))
