# Phase 3.10 — Deterministic Governance Envelope Simulator

## Purpose

Simulate deterministic governance enforcement around the dry-run engineering transaction chain.

This phase validates rejection/allowance decisions without enabling mutation.

## Inputs

- transaction summary
- mutation simulator artifact
- recovery simulator artifact

## Forbidden Operations

- no git apply
- no config mutation
- no service restart
- no rollback restore
- no worker execution
- no apply wrapper execution
- no runtime source-of-truth mutation

## Output Root

watch/governance-sim/runs/

## Required Governance Cases

### phase_mismatch

Reject transaction whose declared phase does not match expected phase.

Expected:
- governance_allowed=false
- rejection_reason=phase_mismatch

### unauthorized_role

Reject action assigned to unauthorized role.

Expected:
- governance_allowed=false
- rejection_reason=unauthorized_role

### invalid_review_verdict

Reject invalid or non-PASS review verdict.

Expected:
- governance_allowed=false
- rejection_reason=invalid_review_verdict

### missing_backup_binding

Reject transaction with missing backup binding.

Expected:
- governance_allowed=false
- rejection_reason=missing_backup_binding

### missing_rollback_binding

Reject transaction with missing rollback binding.

Expected:
- governance_allowed=false
- rejection_reason=missing_rollback_binding

### replayed_transaction

Reject replayed transaction.

Expected:
- governance_allowed=false
- rejection_reason=replayed_transaction

### stale_validator

Reject stale validator result.

Expected:
- governance_allowed=false
- rejection_reason=stale_validator

### governance_drift

Reject governance drift.

Expected:
- governance_allowed=false
- rejection_reason=governance_drift

### clean_envelope

Permit only clean non-mutating simulated envelope.

Expected:
- governance_allowed=true
- rejection_reason=null

## Governance Invariants

- mutation_performed must remain false
- execution_performed must remain false
- rollback_performed must remain false
- simulator may only write under watch/governance-sim/runs/
