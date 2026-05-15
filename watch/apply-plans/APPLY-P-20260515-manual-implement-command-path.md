# Spot Apply Plan APPLY-P-20260515-manual-implement-command-path

linked_proposal: P-20260515-manual-implement-command-path
approved_utc: 20260515-014748
generated_utc: 20260515-015723
task: Implement approved Codex API patch proposal endpoint path as non-mutating command workflow.
risk_class: low
apply_status: pending_manual_review
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
- /home/ogre/spot-stack/watch/spot-ops.sh

PRECHANGE_BACKUP_REQUIREMENTS
- Before any future mutation, Spot Core must create and verify a pre-change backup on Unimatrix.
- Required backup root: /mnt/collective/backups/<target>/<service>/<timestamp>/
- Backup path must be recorded in the action log before execution begins.
- If backup creation or verification fails, execution remains blocked.

PRECHECK_VALIDATION
- bash -n /home/ogre/spot-stack/watch/spot-client.sh
- bash -n /home/ogre/spot-stack/watch/spot-ops.sh
- spot validate

PLANNED_MUTATIONS
- Add and validate the non-mutating implement command path that routes approved W-6 proposals to W-3 coding artifact generation.
- This apply plan does not execute mutations.
- Future execution must route through Spot Core policy/enforcement wrappers.

POST_APPLY_VALIDATION
- bash -n /home/ogre/spot-stack/watch/spot-client.sh
- bash -n /home/ogre/spot-stack/watch/spot-ops.sh
- spot validate

ROLLBACK_PLAN
- Use Spot Core pre-change backup/apply-plan rollback if this implementation proposal later becomes an approved apply plan.
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
