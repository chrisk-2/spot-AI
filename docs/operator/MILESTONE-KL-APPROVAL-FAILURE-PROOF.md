# Milestone K/L — Approval Escalation and Failure Injection Proof

## Status

Implemented as metadata-only governance proof.

## Scope

This lane adds:

- approval escalation records
- denial/block records
- failure/crash proof records
- safe-failure validation

## Invariants

- Spot Core remains sole executor.
- Workers do not self-apply.
- Approval records do not grant execution authority.
- Failure proofs do not execute rollback.
- All records preserve execution_allowed=false.
- All records preserve mutation_authority=false.
- Failure proofs must validate as safe failure records.

## Acceptance

Acceptance requires:

- approval writer, show, validate pass
- failure proof writer, show, validate pass
- synthetic operator-denied proof records safely
- synthetic replay-block proof records safely
- normal spot validate remains PASS
