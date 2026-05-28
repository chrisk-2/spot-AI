# Module — Governed Recovery Replay Simulation

## Scope

Adds a read-only governed recovery replay simulation model.

## Purpose

Define deterministic replay requirements for future recovery transaction audits.

## Replay Inputs

- replay id
- request id
- action id
- recovery id
- target
- service
- risk class
- execution lease id
- replay token id
- approval id
- backup binding id
- rollback binding id
- execution receipt id
- receipt chain id
- validation result
- rollback decision
- final outcome
- journal path

## Replay Rules

- replay is audit-only
- replay cannot execute recovery
- replay cannot restore files
- replay cannot restart services
- replay requires full receipt chain
- replay requires rollback binding
- replay requires validation proof
- replay mismatch blocks recovery closure
- replay result must be journaled

## Safety Boundary

This module is advisory/read-only.

It does not execute, restore, rollback, restart, approve, mutate, or bypass governance.
