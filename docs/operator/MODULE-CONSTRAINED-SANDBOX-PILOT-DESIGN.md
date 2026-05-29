# Module — Constrained Sandbox Pilot Design

## Purpose

Define the first controlled sandbox execution pilot.

This module is design-only.

It does not enable live execution.

## Current Governance State

- mode: read_only
- advisory_only: true
- execution_allowed: false
- mutation_authority: false
- live_executor_enabled: false
- worker_self_apply_allowed: false

## Pilot Goal

Prove the future executor can perform one harmless, reversible action inside a dedicated sandbox path only.

## Allowed Sandbox Path

- /tmp/spot-sandbox-pilot/

## Allowed Future Actions

Only after explicit approval in a later module:

- create a test file inside /tmp/spot-sandbox-pilot/
- write non-sensitive test content
- verify checksum
- restore/delete using rollback plan

## Forbidden Actions

- no service restart
- no system config mutation
- no firewall mutation
- no DNS mutation
- no DHCP mutation
- no routing mutation
- no SSH mutation
- no production path writes
- no worker self-apply
- no backup deletion
- no audit deletion
- no execution outside the sandbox path

## Required Gates Before Any Future Sandbox-Live Test

- explicit operator approval
- backup artifact path recorded
- rollback plan defined
- kill switch present
- immutable action journal path defined
- deterministic validator present
- Spot Core remains sole executor
- governance mode change documented

## Backup Requirement

Before a sandbox-live pilot, the executor must create a pre-action backup under:

- /mnt/collective/backups/spot-sandbox-pilot/

The backup must contain:

- metadata.json
- checksum marker
- source state snapshot
- rollback instructions

## Rollback Requirement

Rollback must be defined before execution.

For the sandbox pilot, rollback means:

- remove created test file
- restore previous sandbox state from backup
- verify final state
- write rollback result to journal

## Kill Switch

Future implementation must support a hard stop file:

- watch/state/executor-kill-switch.enabled

If present, execution must be blocked.

## Audit Requirement

Future sandbox-live action must append immutable evidence under:

- /mnt/collective/logs/spot/actions/
- /mnt/collective/logs/spot/rollbacks/

## Promotion Criteria

The sandbox pilot may not promote to broader execution unless:

- sandbox backup verified
- sandbox rollback verified
- action journal valid
- rollback journal valid
- replay validator passes
- governance validator passes
- operator explicitly approves next scope

## Design Result

This module only authorizes design readiness.

It does not authorize sandbox-live execution.
