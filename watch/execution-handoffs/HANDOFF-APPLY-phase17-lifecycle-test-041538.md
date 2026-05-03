# Spot Execution Handoff HANDOFF-APPLY-phase17-lifecycle-test-041538

linked_apply_plan: APPLY-phase17-lifecycle-test-041538
linked_proposal: TEST-PROPOSAL
generated_utc: 20260503-041538
apply_status: review_approved
risk_class: clean_risk
execution_allowed: false
mutation_allowed: false
backup_required: true
backup_bound: false
backup_artifact: pending
policy_class: controlled_execution_handoff
autonomy_level: 1
execution_wrapper_required: true
executor: spot-core-controlled-wrapper
approval_gate: wrapper_execution_approval_required
rollback_required: true
rollback_authority: recorded_prechange_backup_only

---

PURPOSE
- Prepare reviewed apply-plan context for a future Spot Core controlled execution wrapper.
- This artifact does not authorize execution.
- This artifact does not mutate files.
- This artifact does not bind a backup.

FUTURE_EXECUTION_REQUIREMENTS
- Spot Core must create and verify a pre-change backup before mutation.
- Spot Core must record the verified backup artifact path before execution.
- Spot Core must execute through a controlled policy/enforcement wrapper.
- Spot Core must run post-apply validation.
- Spot Core must rollback from the recorded backup artifact if validation fails.

TARGET_FILES
- /home/ogre/spot-stack/watch/spot-client.sh

PRECHANGE_BACKUP_REQUIREMENTS
- create backup

PRECHECK_VALIDATION
- python3 -m json.tool /home/ogre/spot-stack/spot-core/config/cluster_config.json >/dev/null
- spot validate
- spot ask "show worker latency"
- spot ask "what is the current fleet status"
- spot ask "show current routing audit"

PLANNED_MUTATIONS
- none

POST_APPLY_VALIDATION
- spot validate

ROLLBACK_PLAN
- restore backup

HUMAN_REVIEW_GATE
- manual review required

POLICY_GATES
- No backup, no change.
- Detect -> Analyze -> Classify -> Backup -> Plan -> Verify -> Execute -> Test/Rollback.
- Execution remains blocked until a future Spot Core wrapper binds backup_artifact and changes execution_allowed under policy.
- Memory and proposal history are context only, not authorization.

NOTES
- Generated from apply-plan: APPLY-phase17-lifecycle-test-041538.md
- Current handoff state is non-executing.
