POLICY governance_v1

INVARIANT spot_core_sole_executor = true
INVARIANT worker_self_apply = forbidden
INVARIANT codex_mutation = forbidden
INVARIANT openai_mutation = forbidden

RULE no_backup_no_execution
REQUIRE backup_binding = verified

RULE no_rollback_no_execution
REQUIRE rollback_binding = verified

RULE no_review_no_execution
REQUIRE review_verdict = PASS

RULE no_unsigned_approval
REQUIRE approval_artifact = signed

RULE high_risk_requires_quorum
REQUIRE quorum_level = enforced

RULE production_network_mutation
ACTION = blocked

RULE routing_authority_mutation
ACTION = blocked
