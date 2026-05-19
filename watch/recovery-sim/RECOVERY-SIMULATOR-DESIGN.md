# Phase 3.9 — Recovery Orchestration Simulator

## Purpose

Simulate transaction recovery behavior without live mutation.

This phase validates:

- interrupted transaction recovery
- replay denial
- orphaned transaction detection
- stale transaction expiry
- recovery journal chain integrity

## Forbidden Operations

- no git apply
- no config mutation
- no service restart
- no rollback restore
- no worker execution
- no runtime source-of-truth mutation

## Output Root

watch/recovery-sim/runs/

## Required Recovery States

### interrupted_rehydrate

Rehydrates an interrupted simulator transaction into a recovery candidate.

Expected:
- recovery_required=true
- rehydrated=true
- mutation_performed=false
- execution_performed=false

### replay_denied

Blocks a transaction replay attempt.

Expected:
- replay_blocked=true
- recovery_allowed=false

### orphan_detected

Detects missing parent transaction linkage.

Expected:
- orphan_detected=true
- recovery_allowed=false

### stale_expired

Marks stale transaction as expired.

Expected:
- stale_expired=true
- recovery_allowed=false

### journal_chain

Builds recovery chain reference.

Expected:
- journal_chain_valid=true
- recovery_allowed=true

## Governance Invariants

- recovery simulation may not restore rollback artifacts
- recovery simulation may not execute apply wrappers
- recovery simulation may only write under watch/recovery-sim/runs/
