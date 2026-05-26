# Module — Governed Execution Leasing

## Scope

Adds read-only execution lease modeling.

## Purpose

Prevent future executor races by requiring any proposed execution path to declare:

- executor authority
- lease owner
- lease scope
- lease TTL
- rollback binding requirement
- backup binding requirement
- review binding requirement

## Safety Boundary

This module is advisory/read-only.

It does not:

- execute commands
- restart services
- write runtime config
- mutate worker state
- authorize remediation
- bypass review, backup, rollback, or Spot Core authority

## Hard Rules

- Spot Core remains sole executor.
- Workers never self-apply.
- No backup means no change.
- No rollback means no execution.
- No review means no apply.
