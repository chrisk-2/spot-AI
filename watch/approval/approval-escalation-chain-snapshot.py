#!/usr/bin/env python3
import json
from datetime import datetime, timezone

data = {
    "module": "deterministic_approval_escalation_chain",
    "mode": "read_only",
    "advisory_only": True,
    "execution_allowed": False,
    "mutation_authority": False,
    "executor": "spot-core",
    "approval_schema": {
        "request_id_required": True,
        "action_id_required": True,
        "target_required": True,
        "service_required": True,
        "risk_class_required": True,
        "review_verdict_required": True,
        "execution_lease_id_required": True,
        "backup_binding_id_required": True,
        "rollback_binding_id_required": True,
        "execution_window_id_required": True,
        "replay_token_id_required": True,
        "receipt_id_required": True,
        "approval_status_required": True,
        "approval_authority_required": True,
        "journal_path_required": True
    },
    "escalation_rules": {
        "low_risk_requires_deterministic_gates": True,
        "medium_risk_requires_allowlist_or_approval": True,
        "high_risk_requires_explicit_approval": True,
        "network_changes_require_explicit_approval": True,
        "firewall_changes_require_explicit_approval": True,
        "dns_changes_require_explicit_approval": True,
        "dhcp_changes_require_explicit_approval": True,
        "vlan_changes_require_explicit_approval": True,
        "ssh_changes_require_explicit_approval": True,
        "reviewer_self_approval_forbidden": True,
        "worker_execution_approval_forbidden": True,
        "openai_execution_approval_forbidden": True,
        "codex_execution_approval_forbidden": True,
        "spot_core_enforces_approval_only": True,
        "approval_does_not_bypass_backup": True,
        "approval_does_not_bypass_rollback": True,
        "approval_does_not_bypass_review": True
    },
    "generated_at": datetime.now(timezone.utc).isoformat()
}

print(json.dumps(data, indent=2, sort_keys=True))
