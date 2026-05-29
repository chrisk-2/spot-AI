# Module — Execution State Drift Detection

## Scope

This module adds read-only execution state drift detection.

It compares modeled governance artifacts for consistency and reports drift without changing runtime state.

## Added

- watch/governance/execution-state-drift-snapshot.py
- watch/governance/execution-state-drift-validate.py
- watch/governance/execution-state-drift-history.py
- operator command: execution-state-drift
- operator command: execution-state-drift-validate
- operator command: execution-state-drift-history

## Output

- watch/state/execution-state-drift.json
- watch/state/execution-state-drift-history.jsonl

## Drift Classes

- NONE
- LEASE_MISSING
- LEASE_WITHOUT_RECEIPT
- RECEIPT_WITHOUT_LEASE
- ROLLBACK_BINDING_MISSING
- RECONCILIATION_MISMATCH
- REPLAY_AUDIT_MISSING
- APPROVAL_STATE_MISMATCH
- GOVERNANCE_STATE_MISMATCH

## Safety Boundary

This module is read-only.

It does not:

- execute actions
- restart services
- modify routing
- modify leases
- modify receipts
- modify rollback bindings
- grant mutation authority
- grant live executor authority

## Governance Invariants

Expected state remains:

- mode: read_only
- execution_allowed: false
- mutation_authority: false
- advisory_only: true

## Validation

The validator checks:

- snapshot exists
- snapshot is valid JSON
- all drift records have known classifications
- governance mode remains read_only
- execution_allowed is false
- mutation_authority is false
- history is append-only JSONL
