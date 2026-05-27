#!/usr/bin/env python3
import json
from datetime import datetime, timezone

data = {
    "module": "immutable_execution_receipt_registry",
    "mode": "read_only",
    "advisory_only": True,
    "execution_allowed": False,
    "mutation_authority": False,
    "executor": "spot-core",
    "receipt_schema": {
        "receipt_id_required": True,
        "request_id_required": True,
        "action_id_required": True,
        "executor_required": True,
        "target_required": True,
        "service_required": True,
        "risk_class_required": True,
        "execution_lease_id_required": True,
        "review_id_required": True,
        "backup_binding_id_required": True,
        "rollback_binding_id_required": True,
        "validation_command_required": True,
        "validation_result_required": True,
        "final_outcome_required": True,
        "journal_path_required": True,
        "timestamp_required": True
    },
    "immutability_rules": {
        "append_only": True,
        "overwrite_forbidden": True,
        "delete_forbidden": True,
        "receipt_does_not_authorize_execution": True,
        "missing_receipt_blocks_completion": True
    },
    "generated_at": datetime.now(timezone.utc).isoformat()
}

print(json.dumps(data, indent=2, sort_keys=True))
