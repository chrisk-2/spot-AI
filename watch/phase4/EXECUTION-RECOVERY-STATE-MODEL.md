# Phase 4 Execution Recovery State Model

## Purpose

Define crash-safe recovery semantics for the Phase 4 noop executor lane.

This document does not authorize live mutation.

## Scope

Applies only to deterministic noop execution modeling.

Forbidden in this phase:

- git apply
- config mutation
- service restart
- rollback restore
- worker execution
- live remediation

## Recovery Principle

Recovery must never convert uncertainty into success.

If execution state is incomplete, ambiguous, duplicated, stale, or replayed, Spot Core must classify it as blocked or requires inspection.

## Recovery Authority

Only Spot Core may classify recovery state.

Workers, Codex, OpenAI, and review nodes may not:

- mark recovery successful
- retry execution
- resolve leases
- promote partial receipts
- bypass governance envelope checks

## Recovery States

Allowed recovery classifications:

- clean_success
- clean_blocked
- incomplete_before_receipt
- partial_receipt
- stale_lease
- replay_detected
- orphaned_lease
- governance_unknown
- requires_operator_inspection

## Receipt Write Rule

A receipt is authoritative only when:

- receipt JSON is valid
- receipt_id is present
- execution_id is present
- request_id is present
- final_outcome is present
- mutation_performed is explicitly false for noop mode
- executor is spot-core
- phase is 4

Invalid or partial receipts must never be treated as success.

## Execution Identity Rule

The execution_id must be deterministic from governed execution material.

The same execution_id may be observed again only when all bound material is identical.

If the same execution_id appears with different material, recovery state must be replay_detected.

## Lease Recovery Rule

Lease ownership must be revalidated after restart.

Execution may not continue from a stale lease.

If a lease exists without a valid matching receipt, recovery state must be orphaned_lease or incomplete_before_receipt.

If a receipt exists after lease expiry, recovery must classify by receipt validity and final_outcome, not by lease existence alone.

## Governance Recovery Rule

Crash recovery must not bypass the governance envelope.

If the governance envelope is missing, malformed, stale, or inconsistent with the receipt, recovery state must be governance_unknown or requires_operator_inspection.

## Crash Cases

### interrupted_before_receipt

Condition:

- governance envelope exists
- lease may exist
- no receipt exists

Recovery state:

- incomplete_before_receipt

Required action:

- do not retry automatically
- require replay guard evaluation
- require lease state inspection
- require new governance evaluation before any new execution attempt

### interrupted_after_receipt

Condition:

- valid receipt exists
- final_outcome exists
- mutation_performed is false
- noop mode confirmed

Recovery state:

- clean_success or clean_blocked based on final_outcome

Required action:

- do not re-execute
- treat receipt as authoritative

### partial_receipt_write

Condition:

- receipt path exists
- JSON invalid or required fields missing

Recovery state:

- partial_receipt

Required action:

- block replay
- require operator inspection
- do not promote to success

### stale_lease_replay

Condition:

- previous lease is expired or not owned by current executor context
- replay attempt uses old lease_id or execution_id

Recovery state:

- stale_lease or replay_detected

Required action:

- block execution
- require new governance envelope
- require new lease

### duplicate_execution_id

Condition:

- execution_id already exists
- bound material differs

Recovery state:

- replay_detected

Required action:

- block execution
- preserve evidence
- require operator inspection

### orphaned_lease

Condition:

- lease exists
- no valid receipt exists
- execution outcome unknown

Recovery state:

- orphaned_lease

Required action:

- do not assume success
- require lease inspection
- require governance inspection

## Required Recovery Proofs

The recovery model must prove:

- receipt written once
- execution_id never reused for different material
- incomplete execution never auto-promoted to success
- lease ownership revalidated after restart
- replay guard survives restart
- crash recovery cannot bypass governance envelope
- recovery path remains Spot Core only
- noop mode never mutates during recovery

## Phase 4 Acceptance Criteria

This recovery model is satisfied when future simulator cases can prove:

- interrupted_before_receipt blocks safely
- interrupted_after_receipt resolves from receipt only
- stale_lease_replay blocks safely
- duplicate execution material is detected
- invalid receipt JSON blocks safely
- no recovery path enables mutation

