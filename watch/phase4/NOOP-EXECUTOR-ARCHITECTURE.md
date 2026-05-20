# Phase 4 — Controlled Noop Executor Architecture

## Purpose

Define the first real executor architecture without enabling live mutation.

The noop executor proves execution lifecycle mechanics while performing no infrastructure change.

## Scope

### Allowed

- create immutable execution receipt
- create noop execution journal
- validate lease ownership model
- validate kill-switch model
- validate approval escalation model
- validate rollback precondition model

### Forbidden

- git apply
- config mutation
- service restart
- rollback restore
- worker execution
- production file mutation
- network mutation

## Executor Rule

Spot Core remains the only executor authority.

### Workers may

- plan
- build artifacts
- review artifacts
- recommend fixes

### Workers may not

- execute
- approve their own work
- mutate runtime
- restore rollback
- bypass Spot Core

## Noop Executor Lifecycle

1. receive approved noop request
2. verify phase allows noop only
3. verify review verdict
4. verify backup/rollback requirements are satisfied or explicitly not required for noop
5. acquire execution lease
6. check kill-switch
7. write immutable start receipt
8. perform noop action
9. write immutable completion receipt
10. release lease
11. validate receipt chain

## Required Receipts

- request_id
- execution_id
- lease_id
- phase
- executor
- action_type
- mutation_performed=false
- execution_performed=true
- noop_performed=true
- rollback_required=false
- rollback_performed=false
- kill_switch_checked=true
- final_outcome

## Phase 4 Exit Criteria

Phase 4 is complete when a noop executor can prove:

- deterministic receipt generation
- lease acquisition/release
- kill-switch enforcement
- replay-safe execution identity
- no mutation
- no rollback restore
- validator PASS
