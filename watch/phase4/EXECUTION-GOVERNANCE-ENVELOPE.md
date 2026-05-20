# Phase 4 Execution Governance Envelope

## Purpose

Define the required governance envelope that must exist before any future executor can produce an execution receipt.

This document does not authorize live mutation.

## Scope

Applies to Phase 4 noop execution modeling only.

Forbidden in this phase:

- git apply
- config mutation
- service restart
- rollback restore
- worker execution
- live remediation

## Required Envelope Fields

Each execution attempt must be bound to a governance envelope containing:

- envelope_id
- request_id
- execution_id
- phase
- executor
- action_type
- target
- risk_class
- approval_state
- review_state
- backup_state
- rollback_state
- lease_id
- kill_switch_state
- replay_guard
- created_at

## Required State Values

### approval_state

Allowed values:

- not_required
- required
- approved
- denied

### review_state

Allowed values:

- not_required
- pending
- pass
- fix
- no

### backup_state

Allowed values:

- not_required
- required
- verified
- failed

### rollback_state

Allowed values:

- not_required
- required
- defined
- failed

### kill_switch_state

Allowed values:

- clear
- active

## Execution Permission Rule

Execution may proceed only when all required gates are satisfied.

For Phase 4 noop execution:

- phase must equal 4
- executor must equal spot-core
- action_type must equal noop
- kill_switch_state must equal clear
- lease_id must be present
- replay_guard must be present
- approval_state must not equal denied
- review_state must not equal fix or no
- backup_state must not equal failed
- rollback_state must not equal failed

## Replay Guard

The replay guard must bind:

- request_id
- execution_id
- action_type
- target
- lease_id
- phase
- executor

The same execution_id must never be reused for different material.

## Receipt Binding

Every execution receipt must reference or embed enough envelope material to prove:

- governance was evaluated before execution
- lease ownership was checked before execution
- kill switch was checked before execution
- replay guard was calculated before execution
- no mutation occurred in noop mode

## Required Safety Proofs

The governance envelope must prove:

- no orphan execution
- no duplicate execution
- no replayed execution_id
- no execution outside lease ownership
- no execution without governance evaluation
- no mutation under noop action_type
- no rollback restore under Phase 4

## Crash-Recovery Semantics

If executor crash occurs before receipt write:

- execution is treated as incomplete
- replay guard blocks unsafe duplicate execution
- recovery must require inspection of envelope and lease state

If executor crash occurs after receipt write:

- receipt is authoritative
- final_outcome controls recovery classification
- no implicit retry may occur without new governance evaluation

## Phase 4 Acceptance Criteria

This document is satisfied when:

- noop simulator can produce receipts
- validator proves deterministic execution identity
- blocked cases produce blocked receipts
- mutation flags remain false
- receipt identity remains stable across repeated validation
- governance envelope requirements are documented before implementation

