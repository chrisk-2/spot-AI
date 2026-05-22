# Milestone N/O — Controlled Remediation and Rollback-on-Failure Proof

## Status

Implemented as controlled sandbox remediation proof.

## Scope

This lane adds:

- controlled low-risk remediation proof
- pre-change backup proof
- rollback definition proof
- rollback-on-validation-failure proof
- rollback verification proof

## Invariants

- No production path is touched.
- No service restart is performed.
- No worker self-apply occurs.
- Spot Core remains sole executor.
- Rollback is defined.
- Rollback is verified.
- Rollback-on-failure restores the pre-failure hash.
- All records preserve execution_allowed=false.
- All records preserve mutation_authority=false.

## Acceptance

Acceptance requires:

- controlled remediation run succeeds
- controlled remediation validator passes
- rollback-on-failure proof succeeds
- rollback-on-failure validator passes
- normal spot validate remains PASS
