# Milestone P/Q/R — Governed Expansion, Learning Proposal Loop, and Acceptance Gate

## Status

Implemented as final controlled-autonomy acceptance aggregation.

## Scope

This lane adds:

- proposal-only learning records
- governed remediation expansion marker
- final acceptance aggregation
- controlled autonomy readiness proof

## Invariants

- Learning is proposal-only.
- Learning requires review.
- Learning cannot auto-apply.
- Acceptance does not authorize live production mutation.
- Spot Core remains sole executor.
- Workers do not self-apply.
- All records preserve execution_allowed=false.
- All records preserve mutation_authority=false.

## Acceptance

Acceptance requires all evidence classes to exist:

- chain
- receipt
- lease
- rollback
- noop
- bundle
- approval
- failure
- sandbox
- remediation
- rollback_failure
- learning

Final acceptance means the governance architecture is ready for controlled autonomy policy review, not unrestricted live production mutation.
