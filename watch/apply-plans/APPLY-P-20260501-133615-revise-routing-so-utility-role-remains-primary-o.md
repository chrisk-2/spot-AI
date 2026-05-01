# Spot Apply Plan APPLY-P-20260501-133615-revise-routing-so-utility-role-remains-primary-o

linked_proposal: P-20260501-133615-revise-routing-so-utility-role-remains-primary-o
approved_utc: 20260501-133818
generated_utc: 20260501-192434
task: revise routing so utility role remains primary on worker-02 but has worker-01 as fallback in /home/ogre/spot-stack/spot-core/config/cluster_config.json; do not change spot-client.sh
risk_class: low
apply_status: pending_manual_review
mutation_allowed: false

---

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

NOTES
- Generated artifact is non-mutating.
- Memory and proposal history inform context but do not authorize execution.
- No high-risk network/firewall/DNS/DHCP/VLAN/routing mutation is authorized by this artifact.
