# Spot Apply Plan APPLY-P-20260511-161823-using-only-this-prompt-and-discovered-spot-ui-01

linked_proposal: P-20260511-161823-using-only-this-prompt-and-discovered-spot-ui-01
approved_utc: 20260511-162455
generated_utc: 20260511-164543
task: Using only this prompt and discovered spot-ui-01 files, produce a coding implementation proposal only. Target exact files only: watch/spot-ui-readiness.sh, watch/spot-ui-render-html.sh, watch/spot-ui-render-risk.sh, watch/spot-ui-risk.json.jq, watch/spot-ui-01.sh, spot-core/spot-ui-01-dashboard-design.md. Primary data source shape includes generated_at, git.dirty, health.spot_core, health.mcp_local, routing.ok, backups.workers_ok, validation.fresh, self_heal.actions, and status. Do not modify cluster_config.json. Do not use wildcard FILES_AFFECTED. Do not use backup .bak paths. Rollback must be git restore of exact UI files only. Validation must include bash -n for shell scripts, jq -n -f watch/spot-ui-risk.json.jq syntax validation, bash watch/spot-ui-readiness.sh | jq ., and render smoke tests. Proposal only; no code.
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
- watch/spot-ui-readiness.sh
- watch/spot-ui-render-html.sh
- watch/spot-ui-render-risk.sh
- watch/spot-ui-risk.json.jq
- watch/spot-ui-01.sh
- spot-core/spot-ui-01-dashboard-design.md

PRECHANGE_BACKUP_REQUIREMENTS
- Before any future mutation, Spot Core must create and verify a pre-change backup on Unimatrix.
- Required backup root: /mnt/collective/backups/<target>/<service>/<timestamp>/
- Backup path must be recorded in the action log before execution begins.
- If backup creation or verification fails, execution remains blocked.

PRECHECK_VALIDATION
- ```bash
- bash -n watch/spot-ui-readiness.sh
- jq -n -f watch/spot-ui-risk.json.jq
- bash watch/spot-ui-readiness.sh | jq .
- ```

PLANNED_MUTATIONS
- Propose a coding implementation for UI readiness and rendering based on the provided files and current Spot context. Ensure that the implementation targets specific UI scripts and adheres to the given rules.
- This apply plan does not execute mutations.
- Future execution must route through Spot Core policy/enforcement wrappers.

POST_APPLY_VALIDATION
- ```bash
- bash -n watch/spot-ui-readiness.sh
- jq -n -f watch/spot-ui-risk.json.jq
- bash watch/spot-ui-readiness.sh | jq .
- ```

ROLLBACK_PLAN
- ```bash
- git restore watch/spot-ui-readiness.sh watch/spot-ui-render-html.sh watch/spot-ui-render-risk.sh watch/spot-ui-risk.json.jq watch/spot-ui-01.sh spot-core/spot-ui-01-dashboard-design.md
- ```
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
