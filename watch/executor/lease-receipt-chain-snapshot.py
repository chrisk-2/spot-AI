#!/usr/bin/env python3
import json
from datetime import datetime, timezone

data = {
    "module": "immutable_lease_receipt_chaining",
    "mode": "read_only",
    "advisory_only": True,
    "execution_allowed": False,
    "mutation_authority": False,
    "executor": "spot-core",
    "chain_schema": {
        "chain_id_required": True,
        "parent_receipt_id_required": True,
        "lease_id_required": True,
        "replay_token_id_required": True,
        "approval_id_required": True,
        "rollback_binding_id_required": True,
        "execution_receipt_id_required": True,
        "recovery_receipt_id_required": True,
        "chain_status_required": True,
        "integrity_hash_required": True,
        "journal_path_required": True,
        "timestamp_required": True
    },
    "chain_rules": {
        "broken_chain_blocks_execution_completion": True,
        "orphan_receipt_blocks_execution_completion": True,
        "receipt_ordering_required": True,
        "replay_token_must_match_lease": True,
        "approval_chain_must_match_receipt": True,
        "rollback_binding_must_match_receipt": True,
        "integrity_hash_mismatch_blocks_completion": True,
        "append_only_chain_required": True,
        "spot_core_required_for_chain_enforcement": True,
        "chain_does_not_authorize_execution": True
    },
    "generated_at": datetime.now(timezone.utc).isoformat()
}

print(json.dumps(data, indent=2, sort_keys=True))
