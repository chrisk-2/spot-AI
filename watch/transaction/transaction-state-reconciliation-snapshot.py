#!/usr/bin/env python3
import json
from datetime import datetime, timezone

data = {
    "module": "transaction_state_reconciliation",
    "mode": "read_only",
    "advisory_only": True,
    "execution_allowed": False,
    "mutation_authority": False,
    "executor": "spot-core",
    "reconciliation_schema": {
        "transaction_id_required": True,
        "request_id_required": True,
        "action_id_required": True,
        "target_required": True,
        "service_required": True,
        "risk_class_required": True,
        "proposed_state_required": True,
        "approved_state_required": True,
        "lease_state_required": True,
        "token_state_required": True,
        "backup_binding_state_required": True,
        "rollback_binding_state_required": True,
        "execution_receipt_state_required": True,
        "recovery_replay_state_required": True,
        "quorum_state_required": True,
        "journal_state_required": True,
        "final_reconciled_state_required": True
    },
    "reconciliation_rules": {
        "state_mismatch_blocks_transaction_closure": True,
        "missing_journal_blocks_transaction_closure": True,
        "missing_receipt_blocks_transaction_closure": True,
        "missing_rollback_binding_blocks_transaction_readiness": True,
        "missing_backup_binding_blocks_transaction_readiness": True,
        "replay_mismatch_blocks_recovery_closure": True,
        "quorum_mismatch_blocks_readiness": True,
        "reconciliation_is_audit_only": True,
        "reconciliation_does_not_authorize_execution": True,
        "spot_core_required_for_reconciliation_enforcement": True
    },
    "generated_at": datetime.now(timezone.utc).isoformat()
}

print(json.dumps(data, indent=2, sort_keys=True))
