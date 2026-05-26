#!/usr/bin/env python3
import json
from datetime import datetime, timezone

data = {
    "module": "supervised_recovery_model",
    "mode": "read_only",
    "advisory_only": True,
    "execution_allowed": False,
    "mutation_authority": False,
    "executor": "spot-core",
    "recovery_model": {
        "detect_required": True,
        "analyze_required": True,
        "classification_required": True,
        "review_required": True,
        "backup_binding_required": True,
        "rollback_binding_required": True,
        "execution_lease_required": True,
        "immutable_journal_required": True,
        "verification_required": True,
        "rollback_or_halt_required": True,
        "worker_self_apply_forbidden": True,
        "high_risk_approval_required": True
    },
    "recovery_execution_authority": {
        "spot-core": "allowed",
        "workers": "forbidden",
        "openai": "forbidden",
        "codex": "forbidden"
    },
    "generated_at": datetime.now(timezone.utc).isoformat()
}

print(json.dumps(data, indent=2, sort_keys=True))
