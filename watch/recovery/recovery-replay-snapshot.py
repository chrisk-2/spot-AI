#!/usr/bin/env python3
import json
from datetime import datetime, timezone

data = {
    "module": "governed_recovery_replay_simulation",
    "mode": "read_only",
    "advisory_only": True,
    "execution_allowed": False,
    "mutation_authority": False,
    "executor": "spot-core",
    "replay_schema": {
        "replay_id_required": True,
        "request_id_required": True,
        "action_id_required": True,
        "recovery_id_required": True,
        "target_required": True,
        "service_required": True,
        "risk_class_required": True,
        "execution_lease_id_required": True,
        "replay_token_id_required": True,
        "approval_id_required": True,
        "backup_binding_id_required": True,
        "rollback_binding_id_required": True,
        "execution_receipt_id_required": True,
        "receipt_chain_id_required": True,
        "validation_result_required": True,
        "rollback_decision_required": True,
        "final_outcome_required": True,
        "journal_path_required": True
    },
    "replay_rules": {
        "replay_is_audit_only": True,
        "replay_cannot_execute_recovery": True,
        "replay_cannot_restore_files": True,
        "replay_cannot_restart_services": True,
        "replay_requires_full_receipt_chain": True,
        "replay_requires_rollback_binding": True,
        "replay_requires_validation_proof": True,
        "replay_mismatch_blocks_recovery_closure": True,
        "replay_result_must_be_journaled": True,
        "spot_core_required_for_replay_enforcement": True
    },
    "generated_at": datetime.now(timezone.utc).isoformat()
}

print(json.dumps(data, indent=2, sort_keys=True))
