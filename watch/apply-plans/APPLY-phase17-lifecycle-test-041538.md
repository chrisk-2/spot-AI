# Spot Apply Plan APPLY-phase17-lifecycle-test-041538

linked_proposal: TEST-PROPOSAL
approved_utc: 20260503-041538
generated_utc: 20260503-041538
task: phase17 lifecycle test
risk_class: low
apply_status: review_approved
review_approved_utc: 20260503-041538
mutation_allowed: false
backup_required: true
backup_bound: false
backup_artifact: pending
policy_class: supervised_apply_plan
autonomy_level: 1
execution_wrapper_required: true
executor: spot-core-controlled-wrapper
approval_gate: human_review_required
rollback_required: true
rollback_authority: recorded_prechange_backup_only

---

TARGET_FILES
- /home/ogre/spot-stack/watch/spot-client.sh

PRECHANGE_BACKUP_REQUIREMENTS
- Before any future mutation, Spot Core must create and verify a pre-change backup on Unimatrix.
- Required backup root: /mnt/collective/backups/<target>/<service>/<timestamp>/
- Backup path must be recorded in the action log before execution begins.
- If backup creation or verification fails, execution remains blocked.

PRECHECK_VALIDATION
- python3 -m json.tool /home/ogre/spot-stack/spot-core/config/cluster_config.json >/dev/null
- spot validate
- spot ask "show worker latency"
- spot ask "what is the current fleet status"
- spot ask "show current routing audit"

PLANNED_MUTATIONS
- none
- This apply plan does not execute mutations.
- Future execution must route through Spot Core policy/enforcement wrappers.

POST_APPLY_VALIDATION
- python3 -m json.tool /home/ogre/spot-stack/spot-core/config/cluster_config.json >/dev/null
- spot validate
- spot ask "show worker latency"
- spot ask "what is the current fleet status"
- spot ask "show current routing audit"

ROLLBACK_PLAN
- Use the verified pre-change backup artifact generated immediately before any future mutation.
- Rollback must use the recorded pre-change backup artifact.
- Rollback must be validated with the same post-apply validation commands.

HUMAN_REVIEW_GATE
- Confirm proposal is still approved and matches current runtime state.
- Confirm target files still exist and match expected live paths.
- Confirm risk class is correct under Spot Autonomy Policy.
- Confirm backup, validation, and rollback instructions are sufficient before any mutation.

NOTES
- Generated artifact is non-mutating.
- Memory and proposal history inform context but do not authorize execution.
- No high-risk network/firewall/DNS/DHCP/VLAN/routing mutation is authorized by this artifact.
