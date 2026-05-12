# Spot Apply Plan APPLY-P-20260512-172440-phase-2-spot-ui-implementation-add-a-read-only-o

linked_proposal: P-20260512-172440-phase-2-spot-ui-implementation-add-a-read-only-o
approved_utc: 20260512-210302
generated_utc: 20260512-210308
task: Phase 2 Spot UI implementation: add a read-only Operator Command Panel to the Spot UI HTML dashboard. It must be proposal-only, no live writes, no service restarts, no routing changes, no network mutation. The panel should show safe operator commands for status, validation stamp, dashboard publish, self-heal audit, routing audit, and logs. It must preserve governance proposal_only_locked and mutation_performed=false execution_performed=false.
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
- /home/ogre/spot-stack/watch/spot-ui-render-html.sh
- /home/ogre/spot-stack/watch/spot-ui-readiness.sh
- /home/ogre/spot-stack/watch/spot-ui-risk.json.jq

PRECHANGE_BACKUP_REQUIREMENTS
- Before any future mutation, Spot Core must create and verify a pre-change backup on Unimatrix.
- Required backup root: /mnt/collective/backups/<target>/<service>/<timestamp>/
- Backup path must be recorded in the action log before execution begins.
- If backup creation or verification fails, execution remains blocked.

PRECHECK_VALIDATION
- bash -n /home/ogre/spot-stack/watch/spot-ui-render-html.sh
- jq -n -f /home/ogre/spot-stack/watch/spot-ui-risk.json.jq
- bash /home/ogre/spot-stack/watch/spot-ui-readiness.sh | jq .

PLANNED_MUTATIONS
- Add read-only Operator Command Panel to Spot UI HTML dashboard showing safe commands for status, validation, publish, audit, and logs.
- Preserve governance flags: proposal_only_locked, mutation_performed=false, execution_performed=false.
- No live writes, service restarts, routing/network changes. Target files under /home/ogre/spot-stack/watch/spot-ui-*.
- This apply plan does not execute mutations.
- Future execution must route through Spot Core policy/enforcement wrappers.

POST_APPLY_VALIDATION
- bash -n /home/ogre/spot-stack/watch/spot-ui-render-html.sh
- jq -n -f /home/ogre/spot-stack/watch/spot-ui-risk.json.jq
- bash /home/ogre/spot-stack/watch/spot-ui-readiness.sh | jq .

ROLLBACK_PLAN
- git restore /home/ogre/spot-stack/watch/spot-ui-render-html.sh
- git restore /home/ogre/spot-stack/watch/spot-ui-readiness.sh
- git restore /home/ogre/spot-stack/watch/spot-ui-risk.json.jq
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
