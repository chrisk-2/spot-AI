#!/usr/bin/env python3
import json
from datetime import datetime, timezone

data = {
    "module": "execution_lease_ttl_enforcement",
    "mode": "read_only",
    "advisory_only": True,
    "execution_allowed": False,
    "mutation_authority": False,
    "executor": "spot-core",
    "ttl_schema": {
        "lease_id_required": True,
        "request_id_required": True,
        "action_id_required": True,
        "executor_required": True,
        "target_required": True,
        "service_required": True,
        "issued_at_required": True,
        "expires_at_required": True,
        "max_ttl_seconds_required": True,
        "lease_status_required": True,
        "renewal_policy_required": True,
        "journal_path_required": True
    },
    "ttl_rules": {
        "expired_lease_blocks_execution": True,
        "missing_expiry_blocks_execution": True,
        "stale_lease_blocks_execution": True,
        "renewal_requires_new_review": True,
        "renewal_requires_journal_entry": True,
        "lease_does_not_authorize_execution": True,
        "spot_core_required_for_enforcement": True
    },
    "generated_at": datetime.now(timezone.utc).isoformat()
}

print(json.dumps(data, indent=2, sort_keys=True))
