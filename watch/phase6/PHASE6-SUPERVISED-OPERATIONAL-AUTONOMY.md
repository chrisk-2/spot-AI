# Phase 6 — Supervised Operational Autonomy

## Status

Active lane.

## Scope

Phase 6 introduces supervised operational autonomy against controlled fixture services only.

This phase does not authorize production mutation.

## Allowed

- fixture service lifecycle simulation
- governed apply queue simulation
- lease expiration handling
- rollback continuity validation
- immutable journal records
- deterministic validation
- sandbox/fixture-only state mutation

## Forbidden

- production service mutation
- network/firewall/DNS/DHCP/routing mutation
- worker self-apply
- Codex mutation
- OpenAI mutation
- git apply in live environment
- service restart autonomy against production services
- mutation without backup binding
- mutation without rollback binding
- replay-unsafe execution identity

## Phase 6 invariants

- Spot Core remains sole executor.
- All actions are fixture scoped.
- Every mutating fixture operation requires backup and rollback metadata.
- Lease ownership must be valid at execution time.
- Expired leases block execution.
- Verification failure must trigger rollback.
- Replay attempts must be blocked.
- Target escape must be blocked.
- Journals are append-only runtime artifacts.

## Fixture service model

The fixture service is a local state file under a phase-local sandbox path.

Valid states:

- stopped
- starting
- running
- degraded
- failed
- rollback_restored

Valid lifecycle actions:

- start
- stop
- restart
- degrade
- fail
- rollback

## Acceptance criteria

Phase 6 passes when validation proves:

- governed start succeeds
- governed stop succeeds
- governed restart succeeds
- verification failure rolls back
- expired lease blocks execution
- replayed execution identity blocks execution
- target escape blocks execution
- mutation scope remains fixture-only
