# Milestone F/G/H — Lease Ownership, Rollback Receipts, and Deterministic Preflight

## Status

Implemented as metadata-only governance controls.

## Scope

This lane adds:

- execution lease ownership records
- immutable rollback receipts
- deterministic preflight checks across chain, lease, rollback, and receipt artifacts

## Invariants

- Spot Core remains sole executor.
- Workers do not self-apply.
- No live mutation is authorized by this milestone.
- All records preserve `execution_allowed=false`.
- All records preserve `mutation_authority=false`.
- Rollback receipts define rollback but do not execute rollback.
- Preflight can pass only when correlation, lease, rollback, receipt, and required chain artifacts exist.

## Acceptance

Acceptance requires:

- lease writer, show, validate pass
- rollback writer, show, validate pass
- preflight gate passes for a synthetic complete correlation
- operator commands expose lease, rollback, and preflight views
- normal `spot validate` remains PASS
