# Module D1 — Operational Hardening Diagnostics

## Scope

Adds read-only diagnostics for accepted operational warnings:

- backup freshness warning visibility
- /review/local reachability and timeout visibility

## Boundaries

This module does not:

- change execution authority
- enable mutation
- change worker routing ownership
- touch UI files
- restart services
- write to backup history
- alter runtime state

## Commands

Backup freshness diagnostic:

`watch/ops/backup-freshness-diagnostic.py`

Review local diagnostic:

`watch/review/review-local-diagnostic.py`

## Expected result

Diagnostics may return WARN without failing governance.

WARN means operator-visible condition, not execution authorization.

## Governance

Spot Core remains sole executor.

Workers never self-apply.

No backup means no change.
