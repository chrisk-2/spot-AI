#!/usr/bin/env python3
import json
from datetime import datetime, timezone

data = {
    "module": "deterministic_execution_replay_auditing",
    "mode": "read_only",
    "advisory_only": True,
    "execution_allowed": False,
    "mutation_authority": False,
    "executor": "spot-core",
    "audit_schema": {
        "audit_id_required": True,
        "transaction_id_required": True,
        "request_id_required": True,
        "action_id_required": True,
        "executor_required": True,
        "target_required": True,
        "service_required": True,
        "risk_class_required": True,
        "approval_id_required": True,
        "lease_id_required": True,
        "token_id_required": True,
        "backup_binding_id_required": True,
        "rollback_binding_id_required": True,
        "execution_receipt_id_required": True,
        "receipt_chain_id_required": True,
        "quorum_id_required": True,
        "reconciliation_id_required": True,
        "validation_result_required": True,
        "final_outcome_required": True,
        "journal_path_required": True
    },
    "audit_rules": {
        "replay_audit_is_read_only": True,
        "replay_audit_cannot_execute": True,
        "replay_audit_cannot_restore": True,
        "replay_audit_cannot_mutate": True,
        "replay_audit_requires_receipt_chain": True,
        "replay_audit_requires_reconciliation_state": True,
        "replay_audit_requires_quorum_state": True,
        "replay_audit_requires_validation_result": True,
        "mismatch_blocks_audit_closure": True,
        "audit_result_must_be_journaled": True,
        "spot_core_required_for_audit_enforcement": True
    },
    "generated_at": datetime.now(timezone.utc).isoformat()
}

print(json.dumps(data, indent=2, sort_keys=True))
