# Spot Execution Handoff HANDOFF-APPLY-P-20260501-133615-revise-routing-so-utility-role-remains-primary-o

linked_apply_plan: APPLY-P-20260501-133615-revise-routing-so-utility-role-remains-primary-o
linked_proposal: P-20260501-133615-revise-routing-so-utility-role-remains-primary-o
generated_utc: 20260501-214450
apply_status: review_approved
risk_class: low
execution_allowed: false
mutation_allowed: false
backup_required: true
backup_bound: false
backup_artifact: pending

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
- `/home/ogre/spot-stack/spot-core/config/cluster_config.json`

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
- Revise the routing configuration to ensure that worker-02 continues to remain the primary for the utility role while using worker-01 as a fallback.
- No changes will be made to `spot-client.sh`.
- This apply plan does not execute mutations.
- Future execution must route through Spot Core policy/enforcement wrappers.

POST_APPLY_VALIDATION
- python3 -m json.tool /home/ogre/spot-stack/spot-core/config/cluster_config.json >/dev/null
- spot validate
- spot ask "show worker latency"
- spot ask "what is the current fleet status"
- spot ask "show current routing audit"

ROLLBACK_PLAN
- To rollback to the previous state, apply the backup of `cluster_config.json` created before the change was made.
- Rollback must use the recorded pre-change backup artifact.
- Rollback must be validated with the same post-apply validation commands.

HUMAN_REVIEW_GATE
- Confirm proposal is still approved and matches current runtime state.
- Confirm target files still exist and match expected live paths.
- Confirm risk class is correct under Spot Autonomy Policy.
- Confirm backup, validation, and rollback instructions are sufficient before any mutation.

POLICY_GATES
- No backup, no change.
- Detect -> Analyze -> Classify -> Backup -> Plan -> Verify -> Execute -> Test/Rollback.
- Execution remains blocked until a future Spot Core wrapper binds backup_artifact and changes execution_allowed under policy.
- Memory and proposal history are context only, not authorization.

NOTES
- Generated from apply-plan: APPLY-P-20260501-133615-revise-routing-so-utility-role-remains-primary-o.md
- Current handoff state is non-executing.
