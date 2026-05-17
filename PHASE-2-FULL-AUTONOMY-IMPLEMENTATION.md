Phase 2 Full Autonomy Implementation Plan
Starfleet OS / Spot Core
Status: Phase 2.29 complete; next lane is Phase 2.30 design review only.
1. Current position
•	Current position: Phase 2.29 readiness proof aggregation is complete.
•	Readiness checkpoint: READINESS-GATE-CHECKPOINT-20260517-053147.json.
•	Current gate decision: GO_FOR_DESIGN_REVIEW_ONLY.
•	Next allowed lane: live_backup_creation_design_review_only.
•	Next forbidden lane: live_backup_creation_implementation.
2. Prime directive
No backup, no change.
No review, no apply.
No rollback, no execution.
No worker applies its own work.
Spot Core is the only enforcement and apply authority.
3. Final Phase 2 target
Phase 2 is complete when Spot can safely handle approved low/medium-risk operational work from detection through verified remediation.
Detect -> Analyze -> Classify -> Plan -> Review plan -> Build artifact -> Review artifact -> Deterministic preflight -> Approval gate if required -> Backup creation -> Backup verification -> Backup binding -> Execute through Spot Core only -> Post-change verification -> Rollback or halt on failure -> Journal -> Handoff/state update -> Lessons learned proposal
4. Role ownership
Component	Primary job	Hard boundary
Spot Core	Intake, classification, routing, policy, backup, rollback, execution, verification, journal	Only authority allowed to apply changes
Worker-04	Heavy practical planning and remediation design	May plan; may not apply
Worker-06	Reasoning, escalation, ambiguous/high-complexity analysis	May reason/escalate; may not apply
Worker-03	Local coding lane, scripts, validators, small patches, Codex staging	May build; may not approve or apply
Codex	Proposal-only specialized coding assistant	No direct mutation, shell, backup, restart, or apply
Worker-05	Independent review / QC for plans, code, policy fit	Reviews only; PASS/FIX/NO; no execution
OpenAI	Manual external reviewer only	Approval required; no execution; no automatic fallback
5. Worker-05 QC standard
Worker-05 must review against a project-local standard, not generic model judgment. Create and maintain:
watch/review/WORKER-05-QC-STANDARD.md
Every W-5 review bundle must include
•	original request or source alert
•	current phase and gate decision
•	risk class
•	approved plan if any
•	changed files or proposed artifacts
•	patch/diff/process artifact
•	policy requirements
•	forbidden behavior
•	validation commands
•	backup requirements
•	rollback requirements
•	expected verdict schema
W-5 compares against
•	intent
•	approved plan
•	current phase
•	Spot autonomy policy
•	worker role ownership
•	backup and rollback requirements
•	validation proof
6. Required review verdict schema
{
  "verdict": "PASS|FIX|NO",
  "execution_allowed": true,
  "confidence": "low|medium|high",
  "intent_match": "pass|fix|fail",
  "code_match": "pass|fix|fail|not_applicable",
  "policy_match": "pass|fix|fail",
  "phase_match": "pass|fix|fail",
  "backup_required": true,
  "backup_verified": false,
  "rollback_defined": true,
  "validation_defined": true,
  "required_fixes": [],
  "blocking_findings": [],
  "notes": "short reviewer summary"
}
Spot Core may proceed only when verdict is PASS, execution_allowed is true, intent/policy/phase match pass, rollback and validation are defined, and backup requirements are satisfied for mutating work.
7. Full autonomy milestone ladder
Phase 2.30 - Live backup creation design review only
•	Goal: Design the live backup creation system. No implementation.
•	Allowed/proven: Design docs, schemas, failure cases, W-5 QC standard, learning loop.
•	Forbidden: Live backup creation, live source reads, hashing, executor dispatch, config writes, service restarts.
Phase 2.31 - Backup creation implementation, dry-run first
•	Goal: Implement backup creation wrapper in dry-run mode only.
•	Allowed/proven: Code/scripts, synthetic fixtures, dry-run manifests, syntax tests.
•	Forbidden: Live source reads, live backup writes, service restarts, executor dispatch.
Phase 2.32 - Live backup creation, non-mutating target only
•	Goal: Create real backup artifacts without modifying source systems.
•	Allowed/proven: Approved source reads, hashes, new backup directories, metadata and verification markers.
•	Forbidden: Overwrite/delete backups, source mutation, remediation execution, service restarts.
Phase 2.33 - Backup binding gate
•	Goal: Bind verified backup artifact to proposed mutating action.
•	Allowed/proven: Binding records, readable backup verification, pre-execution requirement.
•	Forbidden: Execution without binding, binding to missing/unverified backup, post-execution binding.
Phase 2.34 - Executor wrapper, no-op apply mode
•	Goal: Route execution through final wrapper without mutation.
•	Allowed/proven: Policy checks, review verdict verification, backup binding verification, no-op journal.
•	Forbidden: Actual restart, config write, network change, direct shell mutation.
Phase 2.35 - First live low-risk remediation
•	Goal: Execute one approved low-risk action through the full chain.
•	Allowed/proven: Controlled test service/fixture, backup, binding, Spot Core execution, verification, journal.
•	Forbidden: Firewall, DNS, DHCP, VLAN, routing, SSH, production service config.
Phase 2.36 - Rollback validation
•	Goal: Prove failed verification causes rollback or halt according to policy.
•	Allowed/proven: Controlled failure fixture, rollback evidence, journal.
•	Forbidden: Unsafe production rollback, network/firewall rollback test, silent failure.
Phase 2.37 - Medium-risk controlled autonomy
•	Goal: Allow pre-approved reversible medium-risk actions.
•	Allowed/proven: Known-good config replacement in test lane, container redeploy in approved lane.
•	Forbidden: Unreviewed, unbacked, unverified medium-risk changes.
Phase 2.38 - Worker learning loop
•	Goal: Make the collective improve through reviewed lessons.
•	Allowed/proven: Lesson files, W-5 lesson review, Spot Core accept/reject, validator improvements.
•	Forbidden: Workers rewriting their own authority or learning rules directly.
Phase 2.39 - Full controlled autonomy acceptance
•	Goal: Declare Phase 2 complete after all gates are proven.
•	Allowed/proven: W-5 QC, Codex/OpenAI constraints, live backup, binding, executor, rollback, learning loop.
•	Forbidden: Any bypass of review, backup, rollback, or Spot Core enforcement.
8. Required journals
/mnt/collective/logs/spot/reviews/
/mnt/collective/logs/spot/actions/
/mnt/collective/logs/spot/backups/
/mnt/collective/logs/spot/rollbacks/
/mnt/collective/logs/spot/learning/
Each mutating action must record
•	timestamp
•	request_id
•	action_id
•	target and service
•	risk_class
•	plan_review_id
•	code_review_id
•	backup_path
•	backup_binding_id
•	approval_id if required
•	execution_result
•	verification_result
•	rollback_result
•	final_outcome
9. Safety invariants
•	Codex cannot mutate.
•	OpenAI cannot mutate.
•	W-3/W-4/W-5/W-6 cannot apply.
•	Spot Core applies only after gates pass.
•	No backup means no change.
•	No rollback means no execution.
•	High-risk network actions remain approval-gated.
•	Review PASS does not bypass backup.
•	Backup PASS does not bypass review.
•	Operator approval does not bypass backup or rollback.
10. Current next action
The next action is design-only: implement Phase 2.30 documentation and W-5 QC standard. Do not implement live backup creation yet.
Recommended next files
•	watch/review/WORKER-05-QC-STANDARD.md
•	watch/backup/BACKUP-CREATION-DESIGN.md
•	watch/backup/BACKUP-METADATA-SCHEMA.md
•	watch/backup/BACKUP-FAILURE-CASES.md
•	watch/learning/FLEET-LEARNING-LOOP.md
Validation after adding design docs
•	W-5 reviews design bundle.
•	spot-readiness-gate-checkpoint remains clean.
•	fleet validate remains PASS.
•	No mutation beyond approved design files.
