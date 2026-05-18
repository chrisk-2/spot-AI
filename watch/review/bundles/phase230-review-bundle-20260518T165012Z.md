# Phase 2.30 Review Bundle

Generated:
20260518T165012Z

Commit:
c64ee8784bca1c89b68bb15d1358e2094bd728c5

Validation:
[PASS] governance integrity

=== SUMMARY ===
pass=30 warn=0 fail=0
RESULT: PASS

---

# FILE: PHASE-2-FULL-AUTONOMY-IMPLEMENTATION.md

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


## Deterministic Validation Requirements

Every autonomy phase must define:

- required validation commands
- expected PASS conditions
- required journal entries
- rollback verification requirements
- fail-closed behavior
- escalation conditions
- dry-run proof requirements where applicable

No phase may advance unless:
- validators pass
- required journals exist
- rollback paths are defined
- failure handling is documented
- review gates return PASS

Validation must be deterministic and repeatable.
Model judgment alone is not considered sufficient validation.

## Rollback Verification Requirements

Every mutating workflow must define:

- rollback trigger conditions
- rollback artifact source
- rollback validation method
- rollback success criteria
- rollback halt conditions
- operator escalation conditions

Rollback verification must occur before execution approval.

No mutating workflow may proceed without:
- verified rollback path
- readable rollback artifact
- defined rollback validator
- explicit halt conditions on rollback failure


---

# FILE: watch/review/WORKER-05-QC-STANDARD.md

# Worker-05 QC Standard

## Purpose

Worker-05 is the independent quality-control reviewer for Starfleet OS / Spot Core.

Worker-05 reviews plans, code, process changes, policy fit, intent match, backup requirements, rollback requirements, and validation sufficiency.

Worker-05 does not execute, mutate files, approve its own work, override Spot Core, or bypass policy.

## Authority boundary

Worker-05 may:

- review plans
- review code and patches
- review design documents
- review policy compliance
- review validation evidence
- return PASS, FIX, or NO
- propose required fixes

Worker-05 may not:

- apply changes
- execute commands
- mutate files
- create backups
- bind backups
- restart services
- approve work it generated
- override Spot Core
- approve high-risk actions without required operator approval
- call OpenAI automatically

## Required review inputs

Every review bundle must include:

- review_id
- source request or alert
- current phase
- current gate decision
- task intent
- risk class
- author or builder
- proposed plan or artifact
- changed files, if any
- approved plan, if reviewing code
- policy requirements
- forbidden behavior
- backup requirements
- rollback requirements
- validation commands or validation evidence
- expected verdict schema

If required inputs are missing, Worker-05 must return FIX unless the missing input creates a hard policy violation, in which case it must return NO.

## Review checklist

Worker-05 must check:

1. Intent match

Does the proposal do exactly what was requested, no more?

Fail if it adds hidden scope, new authority, unrelated changes, or unrequested mutation.

2. Phase match

Does the proposal stay inside the current allowed phase?

For Phase 2.30, design documentation is allowed. Live backup creation implementation is forbidden.

3. Policy match

Does the proposal obey Spot autonomy policy?

Required invariants:

- No backup, no change.
- No review, no apply.
- No rollback, no execution.
- Spot Core is the only apply authority.
- Codex is proposal-only.
- OpenAI is manual external review only.
- W-3 builds but does not approve or apply.
- W-4 and W-6 plan/reason but do not apply.
- W-5 reviews only.
- High-risk network changes require approval.

4. Role ownership

Does each component stay in its lane?

- Spot Core: classify, route, enforce, apply, journal.
- W-4: heavy practical planning.
- W-6: reasoning and escalation.
- W-3: local coding/build lane.
- Codex: proposal-only coding assistant.
- W-5: independent review.
- OpenAI: manual external reviewer only.

5. Backup readiness

If the action is mutating, is backup required, defined, and verified before execution?

For design-only phases, Worker-05 must ensure the design does not create live backups or read/hash live source files unless the phase explicitly allows it.

6. Rollback readiness

If the action is mutating, rollback instructions must exist before execution.

If rollback is vague, missing, or invented after the fact, return FIX or NO depending on risk.

7. Validation sufficiency

The proposal must define deterministic validation.

Examples:

- shell syntax checks
- Python compile checks
- fixture tests
- policy rejection tests
- endpoint checks
- validator checks
- journal existence checks

8. Forbidden behavior

Return NO if the proposal allows or performs:

- direct filesystem mutation outside approved scope
- direct admin write bypassing Spot Core
- unrestricted shell
- network mutation without approval
- service restart outside the approved lane
- live backup creation before authorized phase
- backup overwrite or delete
- execution without backup
- execution without rollback
- automatic OpenAI fallback
- worker self-approval
- Codex direct mutation

## Verdict definitions

PASS means:

- intent matches
- phase matches
- policy matches
- role boundaries are preserved
- validation is defined
- backup and rollback requirements are satisfied or not applicable
- no forbidden behavior exists

FIX means:

- proposal is mostly valid but missing required detail
- validation is incomplete
- rollback is underspecified
- backup metadata is incomplete
- review bundle is missing non-critical required fields
- wording is ambiguous but salvageable

NO means:

- policy violation
- wrong phase
- unsafe authority grant
- hidden mutation
- missing backup for mutating action
- missing rollback for mutating action
- automatic OpenAI fallback
- worker self-approval
- Codex or worker direct apply
- high-risk action without approval path

## Required verdict schema

Worker-05 must return machine-readable JSON:

```json
{
  "verdict": "PASS|FIX|NO",
  "execution_allowed": false,
  "confidence": "low|medium|high",
  "intent_match": "pass|fix|fail",
  "code_match": "pass|fix|fail|not_applicable",
  "policy_match": "pass|fix|fail",
  "phase_match": "pass|fix|fail",
  "backup_required": false,
  "backup_verified": false,
  "rollback_defined": false,
  "validation_defined": false,
  "required_fixes": [],
  "blocking_findings": [],
  "notes": "short reviewer summary"
}
eof

## Phase 2.30 QC Closure Requirements

Worker-05 may return PASS for Phase 2.30 only when all of the following are true:

- the reviewed bundle is documentation-only
- no live backup creation is proposed
- no live source reads or hashing are proposed
- no executor dispatch is proposed
- no config writes or service restarts are proposed
- Spot Core remains the only future apply authority
- W-3, W-4, W-5, and W-6 remain non-executing roles
- validation requirements are explicitly documented
- rollback requirements are explicitly documented
- backup validation requirements are explicitly documented
- rollback failure escalation behavior is explicitly documented

For Phase 2.30, backup_required must be false because the reviewed action is documentation-only and non-mutating.
For Phase 2.30, backup_verified must be false because no live backup creation or verification is allowed in this phase.
For Phase 2.30, validation_defined is true when the design documents define deterministic validation requirements for future phases.
For Phase 2.30, rollback_defined is true when the design documents define rollback trigger, artifact source, validator, success criteria, halt conditions, and escalation rules for future mutating phases.

Worker-05 must not fail phase_match merely because Phase 2.30 does not perform live backup creation.
Phase 2.30 is design-review only by definition.

## Required Validator Checklist for Phase 2.30

For Phase 2.30 design review, validation_defined is true only when the design bundle defines the following future validators:

- backup manifest validator
- metadata schema validator
- artifact readability validator
- checksum marker validator
- backup journal validator
- backup binding validator
- rollback plan validator
- rollback artifact readability validator
- rollback success validator
- fail-closed behavior validator
- escalation condition validator
- review verdict schema validator

## Phase 2.30 PASS Conditions

Worker-05 may mark validation_defined=true when the design bundle documents:

- what each validator checks
- what PASS means
- what FAIL means
- what journal entry must exist
- what condition blocks execution
- what condition requires operator escalation

For Phase 2.30, these validators are requirements for future phases only.
They must not be implemented or executed during Phase 2.30.

## Phase 2.30 Fail-Closed and Escalation Requirements

The design bundle must define that any future failed validator:

- blocks execution
- prevents backup binding where backup proof is invalid
- prevents executor dispatch
- writes a failure journal entry
- marks the target degraded when applicable
- requires operator escalation for rollback failure or high-risk uncertainty

No autonomous retry may occur unless a later approved phase explicitly allows it.

## Phase Boundary Clarification

References to Phase 2.31 or later are roadmap requirements only.
They are not implementation proposals in Phase 2.30.

Phase 2.30 remains compliant when it defines future validators, wrapper behavior, backup gates, rollback gates, and learning-loop gates as documentation-only requirements.


---

# FILE: watch/backup/BACKUP-CREATION-DESIGN.md

# Backup Creation Design

## Purpose

This document defines the design for Spot Core live backup creation.

Current phase: Phase 2.30 design review only.

This file does not authorize implementation, live source reads, live hashing, backup creation, backup binding, executor dispatch, service restart, or config mutation.

## Rule

No backup, no change.

Before any mutating action, Spot Core must create and verify a pre-change backup.

The backup must exist before execution.

The backup path must be recorded before execution.

If backup creation or verification fails, the action is blocked.

## Authority

Spot Core owns backup creation.

Workers may plan, propose, or review backup logic.

Workers may not create, delete, overwrite, bind, or apply backups.

Codex is proposal-only.

OpenAI is manual review-only.

## Backup target

Primary backup root:

```text
/mnt/collective/backups/
```

Required target pattern:

```text
/mnt/collective/backups/<target>/<service>/<timestamp>/
```

Timestamp format:

```text
YYYYMMDD-HHMMSSZ
```

## Required backup artifacts

Each backup must eventually contain:

```text
metadata.json
checksums.json or verification-marker.json
backup-created.log
source artifact copies or approved export artifacts
```

Phase 2.30 only designs these artifacts. It does not create them.

## Backup lifecycle

Required future lifecycle:

```text
classify action
resolve target and service
resolve source set
create unique backup directory
copy approved artifacts
write metadata
write checksum or verification marker
verify readability
write backup journal record
expose backup_path to action preflight
```

## Forbidden behavior

Backup creation must never:

- overwrite existing backups
- delete backups
- rename backups
- mutate source files
- perform remediation
- restart services
- write config changes
- dispatch executor actions
- run through Codex directly
- run through any worker directly

## Failure behavior

Any backup failure blocks execution.

Blocking failures include:

- backup root unavailable
- backup directory already exists
- source path missing
- source path outside allowed set
- copy failure
- metadata failure
- checksum or marker failure
- readability verification failure
- journal failure when journal-before-execute is required

## Phase 2.30 allowed work

Allowed:

- design documents
- metadata schema
- failure cases
- review standards
- learning-loop design
- W-5 review of this design

Forbidden:

- live backup creation
- live source reads
- live source hashing
- backup binding
- executor dispatch
- config writes
- service restarts

## W-5 review requirements

Worker-05 must verify:

- this design stays in Phase 2.30 scope
- Spot Core remains the only backup authority
- workers cannot create or modify backups
- Codex cannot mutate
- OpenAI cannot execute
- backup overwrite/delete is forbidden
- failure behavior is fail-closed
- no implementation is included

## Exit criteria

This design is complete when:

- W-5 returns PASS for design review
- metadata schema exists
- failure cases exist
- no implementation was added
- readiness checkpoint remains clean


## Backup Validation Requirements

Backup creation is not considered valid unless:

- metadata.json exists
- backup artifact is readable
- checksum/hash markers exist where required
- backup path is journaled
- backup verification returns PASS
- validator confirms artifact visibility

Failure of any validation step must:
- block execution
- write failure journal entry
- prevent backup binding


---

# FILE: watch/backup/BACKUP-FAILURE-CASES.md

# Backup Failure Cases

## Purpose

This document defines backup failure cases that must block execution.

Current phase: Phase 2.30 design review only.

This file defines required failure behavior only. It does not implement backup creation, read live source files, hash live source files, bind backups, dispatch executors, or mutate configuration.

## Failure principle

Backup failure must fail closed.

If Spot cannot prove that a required backup exists, is verified, and is recorded before execution, Spot Core must block the mutating action.

## Required rejected cases

The future backup implementation must reject these cases.

### backup_root_unavailable

Condition:

```text
/mnt/collective/backups/ is unavailable or not writable for approved backup creation.
```

Expected result:

```text
block execution
record failure
no mutation
```

### backup_directory_already_exists

Condition:

```text
target backup directory already exists
```

Expected result:

```text
block execution
do not reuse directory
do not overwrite existing backup
```

### source_path_missing

Condition:

```text
declared source path does not exist
```

Expected result:

```text
block execution
record missing source
```

### source_path_outside_allowed_set

Condition:

```text
source path is outside the approved source set
```

Expected result:

```text
block execution
record policy violation
```

### unrestricted_source_requested

Condition:

```text
source request includes /, /home, /etc, broad glob, or unbounded recursive copy
```

Expected result:

```text
block execution
record unsafe scope
```

### copy_failure

Condition:

```text
approved source cannot be copied to backup directory
```

Expected result:

```text
block execution
record copy failure
```

### metadata_missing

Condition:

```text
metadata.json was not created
```

Expected result:

```text
block execution
record metadata failure
```

### metadata_invalid_schema

Condition:

```text
metadata.json lacks schema or required fields
```

Expected result:

```text
block execution
record schema failure
```

### metadata_path_mismatch

Condition:

```text
metadata backup_path does not match actual backup directory
```

Expected result:

```text
block execution
record mismatch
```

### checksum_missing

Condition:

```text
checksum or verification marker is absent
```

Expected result:

```text
block execution
record verification failure
```

### checksum_mismatch

Condition:

```text
checksum verification fails
```

Expected result:

```text
block execution
record checksum mismatch
```

### backup_unreadable

Condition:

```text
backup artifact exists but cannot be read back
```

Expected result:

```text
block execution
record readability failure
```

### journal_write_failure

Condition:

```text
required backup journal entry cannot be written before execution
```

Expected result:

```text
block execution when journal-before-execute is required
record journal failure if possible
```

### worker_attempted_backup

Condition:

```text
W-3, W-4, W-5, W-6, Codex, or OpenAI attempts to create or bind backup directly
```

Expected result:

```text
block execution
record authority violation
```

### backup_after_execution

Condition:

```text
backup timestamp is after action execution timestamp
```

Expected result:

```text
block or invalidate action
record ordering violation
```

### backup_delete_or_overwrite_attempt

Condition:

```text
operation attempts to delete, overwrite, rename, or modify existing backup history
```

Expected result:

```text
block execution
record hard policy violation
```

## Required non-mutation assertions

Every failure test must assert:

```text
mutation_performed == false
execution_performed == false
source_modified == false
service_restarted == false
network_mutated == false
```

## Phase 2.30 validation

Phase 2.30 only requires design review of these cases.

No failure harness implementation is authorized by this document.

## Later implementation validation

Future implementation phases must include fixture-based failure tests for each rejected case.

The tests must prove:

- the unsafe case is rejected
- no source file is modified
- no executor dispatch occurs
- no service restart occurs
- no network change occurs
- the failure is journaled or reported

## W-5 review requirements

Worker-05 must verify:

- all major backup failure classes are represented
- failures block execution
- backup history cannot be overwritten or deleted
- workers and providers cannot create backups directly
- ordering requires backup before execution
- failure tests require non-mutation assertions
- this document contains no implementation

## Exit criteria

This failure case design is complete when:

- W-5 returns PASS for design review
- backup creation design references these cases
- metadata schema supports these cases
- no implementation was added


## Rollback Failure Escalation

If rollback fails:

- execution chain halts immediately
- affected target is marked degraded
- Spot Core records rollback failure journal
- autonomous retry is blocked unless policy explicitly allows it
- operator escalation becomes mandatory

No workflow may silently continue after rollback failure.

