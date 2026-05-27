#!/usr/bin/env python3
import json
from datetime import datetime, timezone

data = {
    "module": "replay_safe_execution_token_model",
    "mode": "read_only",
    "advisory_only": True,
    "execution_allowed": False,
    "mutation_authority": False,
    "executor": "spot-core",
    "token_schema": {
        "token_id_required": True,
        "request_id_required": True,
        "action_id_required": True,
        "executor_required": True,
        "target_required": True,
        "service_required": True,
        "risk_class_required": True,
        "lease_id_required": True,
        "review_id_required": True,
        "backup_binding_id_required": True,
        "rollback_binding_id_required": True,
        "receipt_id_required": True,
        "issued_at_required": True,
        "expires_at_required": True,
        "nonce_required": True,
        "token_scope_required": True,
        "journal_path_required": True
    },
    "replay_rules": {
        "single_use_required": True,
        "nonce_required": True,
        "expiry_required": True,
        "scope_binding_required": True,
        "executor_binding_required": True,
        "target_binding_required": True,
        "journal_binding_required": True,
        "reuse_forbidden": True,
        "expired_token_forbidden": True,
        "token_does_not_authorize_execution": True
    },
    "generated_at": datetime.now(timezone.utc).isoformat()
}

print(json.dumps(data, indent=2, sort_keys=True))
