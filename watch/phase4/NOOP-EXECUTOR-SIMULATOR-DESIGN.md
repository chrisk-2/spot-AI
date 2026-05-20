# Phase 4 — Noop Executor Simulator Design

## Purpose

Create the first Phase 4 executor simulator without enabling live mutation.

The simulator proves:

- deterministic execution identity
- execution lease reference
- kill-switch gating reference
- immutable receipt shape
- noop-only execution result
- no mutation
- no rollback restore

## Output Root

watch/phase4/runs/

## Required Cases

### allowed_noop

Expected:

- final_outcome=success
- execution_performed=true
- noop_performed=true
- mutation_performed=false
- rollback_performed=false

### kill_switch_blocked

Expected:

- final_outcome=blocked
- execution_performed=false
- noop_performed=false
- mutation_performed=false

### lease_collision

Expected:

- final_outcome=blocked
- execution_performed=false
- noop_performed=false
- mutation_performed=false

## Forbidden

- git apply
- config mutation
- service restart
- rollback restore
- worker execution
- production file mutation
- network mutation
