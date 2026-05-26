#!/usr/bin/env python3
import json
from datetime import datetime, timezone

data = {
    "module": "approved_remediation_execution_planning",
    "mode": "read_only",
    "advisory_only": True,
    "execution_allowed": False,
    "mutation_authority": False,
    "executor": "spot-core",
    "plan_schema": {
        "request_id_required": True,
        "target_required": True,
        "service_required": True,
        "risk_class_required": True,
        "execution_lease_required": True,
        "review_verdict_required": True,
        "backup_binding_required": True,
        "rollback_binding_required": True,
        "validation_command_required": True,
        "journal_target_required": True,
        "approval_marker_required_when_policy_requires": True
    },
    "execution_authority": {
        "spot-core": "allowed_after_all_gates",
        "spot-worker-01": "forbidden",
        "spot-worker-02": "forbidden",
        "spot-worker-03": "forbidden",
        "spot-worker-04": "forbidden",
        "spot-worker-05": "forbidden",
        "spot-worker-06": "forbidden",
        "codex": "forbidden",
        "openai": "forbidden"
    },
    "blocked_if_missing": [
        "execution_lease",
        "review_verdict",
        "backup_binding",
        "rollback_binding",
        "validation_command",
        "journal_target"
    ],
    "generated_at": datetime.now(timezone.utc).isoformat()
}

print(json.dumps(data, indent=2, sort_keys=True))
