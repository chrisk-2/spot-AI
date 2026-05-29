# Module — Noop Executor Lifecycle Simulation

## Scope

This module adds a read-only noop executor lifecycle simulator.

It models executor lifecycle sequencing without executing commands or mutating runtime state.

## Added

- watch/governance/noop-executor-lifecycle-sim.py
- watch/governance/noop-executor-lifecycle-validate.py
- watch/governance/noop-executor-lifecycle-history.py
- operator command: noop-executor-lifecycle
- operator command: noop-executor-lifecycle-validate
- operator command: noop-executor-lifecycle-history

## Output

- watch/state/noop-executor-lifecycle.json
- watch/state/noop-executor-lifecycle-history.jsonl

## Lifecycle States

- EXECUTOR_CREATED
- EXECUTOR_READY
- EXECUTOR_LEASE_BOUND
- EXECUTOR_RECEIPT_BOUND
- EXECUTOR_APPROVAL_VERIFIED
- EXECUTOR_NOOP_DISPATCH
- EXECUTOR_NOOP_COMPLETE
- EXECUTOR_CLOSED

## Safety Boundary

This module is simulation-only.

It does not:

- execute shell commands
- restart services
- modify config
- modify routing
- create leases
- modify leases
- create execution receipts
- modify receipts
- modify rollback bindings
- grant mutation authority
- grant live executor authority

## Governance Invariants

Expected state remains:

- mode: read_only
- simulation_only: true
- advisory_only: true
- execution_allowed: false
- mutation_authority: false
- live_executor_enabled: false

## Validation

The validator checks:

- lifecycle snapshot exists
- snapshot is valid JSON
- lifecycle states are ordered
- lifecycle is closed
- no mutation authority exists
- no live executor is enabled
- history is valid append-only JSONL
