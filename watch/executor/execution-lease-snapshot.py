#!/usr/bin/env python3
import json
from datetime import datetime, timezone

snapshot = {
    "module": "governed_execution_leasing",
    "mode": "read_only",
    "advisory_only": True,
    "execution_allowed": False,
    "mutation_authority": False,
    "executor": "spot-core",
    "workers_may_self_apply": False,
    "lease_model": {
        "required_for_execution": True,
        "lease_owner_required": True,
        "lease_scope_required": True,
        "lease_ttl_required": True,
        "backup_binding_required": True,
        "rollback_binding_required": True,
        "review_binding_required": True,
        "journal_required": True
    },
    "locked_role_ownership": {
        "general": "spot-worker-01",
        "utility": "spot-worker-02",
        "coding": "spot-worker-03",
        "heavy": "spot-worker-04",
        "review": "spot-worker-05",
        "reasoning": "spot-worker-06"
    },
    "generated_at": datetime.now(timezone.utc).isoformat()
}

print(json.dumps(snapshot, indent=2, sort_keys=True))
