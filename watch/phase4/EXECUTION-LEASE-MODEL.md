# Phase 4 — Execution Lease Model

## Purpose

Prevent duplicate, replayed, or concurrent executor claims.

## Lease Rules

- only Spot Core may acquire an execution lease
- lease_id must be deterministic
- active lease blocks duplicate execution
- stale lease must be recoverable but not silently ignored
- lease release must be recorded
- lease collision must block execution

## Lease States

- requested
- acquired
- released
- stale
- collision_blocked

## Forbidden

- worker-held execution leases
- silent lease replacement
- lease overwrite
- execution without lease
