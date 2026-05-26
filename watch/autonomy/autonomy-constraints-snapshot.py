#!/usr/bin/env python3
import json
from datetime import datetime, timezone

data = {
    "module": "constraint_based_autonomy",
    "mode": "read_only",
    "advisory_only": True,
    "execution_allowed": False,
    "mutation_authority": False,
    "executor": "spot-core",
    "constraints": {
        "executor_must_be_spot_core": True,
        "execution_lease_required": True,
        "review_binding_required": True,
        "backup_binding_required": True,
        "rollback_binding_required": True,
        "validation_binding_required": True,
        "immutable_journal_required": True,
        "worker_self_apply_forbidden": True,
        "openai_execution_forbidden": True,
        "codex_execution_forbidden": True,
        "high_risk_network_mutation_approval_gated": True
    },
    "blocked_without": [
        "review",
        "backup",
        "rollback",
        "validation",
        "journal",
        "lease"
    ],
    "generated_at": datetime.now(timezone.utc).isoformat()
}

print(json.dumps(data, indent=2, sort_keys=True))
