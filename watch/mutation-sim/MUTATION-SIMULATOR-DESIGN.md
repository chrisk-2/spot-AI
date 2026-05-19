# Phase 3.8 — Mutation Simulator

## Purpose

Simulate the full mutation lifecycle without permitting any live mutation.

This phase validates deterministic transaction handling for:

- staged apply
- validation failure
- rollback transition
- interrupted transaction recovery
- replay collision handling

No live mutation is permitted.

## Forbidden Operations

- git apply
- file mutation outside simulator output dirs
- service restart
- live rollback restore
- runtime config modification
- worker execution

## Simulator Output Root

watch/mutation-sim/runs/

Each run creates an immutable simulation artifact set.

## Required Simulation States

### 1. staged_apply
Represents a transaction entering simulated execution.

Expected:
- state=staged_apply
- mutation_performed=false
- execution_performed=false

### 2. validation_failure
Represents deterministic verification failure before apply completion.

Expected:
- state=validation_failure
- rollback_required=true
- rollback_performed=false

### 3. rollback_transition
Represents rollback selection and transition state.

Expected:
- state=rollback_transition
- rollback_required=true
- rollback_simulated=true

### 4. interrupted_transaction
Represents unexpected interruption during simulated apply.

Expected:
- state=interrupted_transaction
- recovery_required=true

### 5. replay_collision
Represents replay-safe collision detection.

Expected:
- state=replay_collision
- replay_blocked=true

## Deterministic Rules

- all IDs derived from deterministic material
- all timestamps UTC ISO8601
- all simulator artifacts immutable
- simulator may only write under:
  watch/mutation-sim/runs/

## Governance Invariants

- Spot Core remains sole executor
- simulator cannot invoke mutation
- simulator cannot invoke rollback restore
- simulator cannot restart services
- simulator cannot bypass apply wrapper gates

