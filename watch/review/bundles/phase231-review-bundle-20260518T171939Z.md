# Phase 2.31 Review Bundle

Generated:
20260518T171939Z

Commit:
715742397f007eb56516715b3e70898684f5b7fe

Validation:
[PASS] governance integrity

=== SUMMARY ===
pass=30 warn=0 fail=0
RESULT: PASS

---

# FILE: watch/backup/PHASE231-DRY-RUN-BACKUP-WRAPPER-SPEC.md

# Phase 2.31 — Dry-Run Backup Wrapper Specification

## Status

Design/specification only.

No live backup writes.
No live source reads.
No service restarts.
No config writes.
No executor dispatch.
No mutation.

## Goal

Define the dry-run backup wrapper contract that will later allow Spot Core to prove backup intent, policy gates, manifest shape, validation sequencing, and journal output without touching live target systems.

## Scope

Phase 2.31 may define:

- dry-run wrapper interface
- dry-run request schema
- dry-run manifest schema
- simulated backup artifact records
- deterministic validator sequence
- fail-closed behavior
- review bundle requirements
- expected journal shape
- future implementation constraints

Phase 2.31 may not perform:

- live source reads
- live hashing of production files
- live backup directory creation
- service mutation
- config mutation
- executor dispatch
- rollback execution

## Dry-Run Wrapper Contract

A dry-run backup wrapper receives:

- request_id
- target
- service
- risk_class
- requested_paths
- proposed_backup_root
- phase
- operator_intent
- review_id if available

The wrapper returns a dry-run manifest only.

The wrapper must not read requested_paths from the target.
The wrapper must not create backup artifacts.
The wrapper must not bind a backup to execution.
The wrapper must not authorize execution.

## Dry-Run Manifest Required Fields

- manifest_version
- timestamp_utc
- phase
- mode
- request_id
- target
- service
- risk_class
- requested_paths
- proposed_backup_root
- proposed_backup_path
- would_create_directories
- would_collect_files
- would_write_metadata
- would_write_checksums
- would_write_journal
- validation_plan
- rollback_plan_required
- execution_allowed
- fail_closed

## Required Static Validators

The dry-run output is valid only if all static validators pass:

- schema validator
- required field validator
- phase boundary validator
- no-live-read validator
- no-live-write validator
- no-executor-dispatch validator
- backup root policy validator
- requested path allowlist validator
- journal shape validator
- rollback requirement validator
- review requirement validator

## PASS Conditions

Phase 2.31 dry-run validation passes only when:

- manifest is valid JSON
- mode is dry_run
- phase is 2.31
- execution_allowed is false
- fail_closed is true
- no live source read occurred
- no live backup write occurred
- no service/config mutation occurred
- proposed backup path is under approved backup root
- rollback requirement is declared
- journal shape is declared
- all static validators pass

## FAIL Conditions

Dry-run validation fails if:

- manifest is missing required fields
- execution_allowed is true
- mode is not dry_run
- live source paths are read
- backup artifacts are created
- executor dispatch is attempted
- backup root is outside approved policy
- rollback requirement is absent
- validation plan is absent
- journal shape is absent

## Fail-Closed Behavior

Any failed validator must:

- block progression
- prevent backup binding
- prevent executor dispatch
- record failure reason in dry-run output
- require review before retry

## Review Requirements

Worker-05 must review Phase 2.31 design/spec changes before any implementation.

Worker-05 review must verify:

- dry-run only
- no live mutation
- no executor dispatch
- required fields present
- validators defined
- fail-closed behavior defined
- rollback and journal requirements preserved

## Phase Exit Criteria

Phase 2.31 exits only when:

- dry-run wrapper spec is committed
- grounded Worker-05 review returns PASS
- spot validate returns PASS
- no live mutation has occurred
