# Milestone M — Sandbox Mutation Pilot

## Status

Implemented as sandbox-only mutation proof.

## Scope

This milestone proves a mutation can occur only inside the sandbox mutation root.

## Invariants

- No production path is touched.
- No service is restarted.
- No worker self-apply occurs.
- Rollback is defined before acceptance.
- Rollback is verified.
- All records preserve execution_allowed=false.
- All records preserve mutation_authority=false.

## Sandbox root

/mnt/collective/logs/spot/sandbox-mutation/work

## Acceptance

Acceptance requires:

- sandbox mutation run succeeds
- target remains under sandbox root
- backup is created before mutation
- rollback artifact matches backup
- sandbox validator passes
- normal spot validate remains PASS
