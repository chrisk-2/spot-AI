# Phase 5 Sandbox Mutation Pilot

## Purpose

Prove Spot can perform a controlled mutation against an isolated sandbox fixture while preserving governance, receipts, journal chaining, verification, and rollback.

This phase does not authorize production mutation.

## Allowed Target

Only sandbox fixture files created under:

    watch/phase5/runs/

## Forbidden Targets

- production config
- system config
- service units
- network config
- firewall/DNS/DHCP/routing
- real worker execution
- git apply
- service restart
- rollback restore outside sandbox fixture

## Required Safety Invariants

- executor is spot-core
- mutation target is sandbox-only
- backup is created before mutation
- rollback path is defined before mutation
- verification runs after mutation
- rollback runs when verification fails
- receipt is written for every case
- journal chain remains valid
- no service restart occurs
- no git apply occurs
- no worker self-apply occurs

## Simulator Cases

- sandbox_mutation_success
- sandbox_verification_failed_rollback
- sandbox_backup_missing_blocked
- sandbox_rollback_missing_blocked
- sandbox_replay_blocked
- sandbox_target_escape_blocked

## Phase 5 Acceptance

Phase 5 is accepted when validation proves:

- successful sandbox mutation
- failed verification causes sandbox rollback
- missing backup blocks execution
- missing rollback blocks execution
- replay attempt blocks execution
- target escape blocks execution
- all receipts are deterministic enough for replay detection
- journal chain validates
- no forbidden mutation path is enabled
