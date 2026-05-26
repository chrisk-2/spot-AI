# Module — Executor Rollback Chain

## Scope

This module documents and normalizes the executor, backup, rollback, and remediation chain.

## Required Chain

Detect
Analyze
Classify
Backup
Bind backup
Review
Preflight
Execute through Spot Core only
Verify
Rollback or halt
Journal

## Preserved Policy

- No backup means no change.
- No rollback means no execution.
- No review means no apply.
- Spot Core remains sole executor.
- Workers do not self-apply.
- OpenAI and Codex remain proposal/review only.
- Runtime state remains separate from source-controlled config.

## Operator Requirement

All future mutating modules must use explicit backup, rollback, validation, and journal paths before execution.

## Status

Initial normalization checkpoint.
