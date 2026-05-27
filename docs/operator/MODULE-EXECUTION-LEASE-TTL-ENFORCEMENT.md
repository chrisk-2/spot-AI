# Module — Execution Lease TTL Enforcement

## Scope

Adds a read-only execution lease TTL enforcement model.

## Purpose

Define expiry and freshness rules for future governed execution leases.

## Required TTL Fields

- lease id
- request id
- action id
- executor
- target
- service
- issued at
- expires at
- max ttl seconds
- lease status
- renewal policy
- journal path

## TTL Rules

- expired leases block execution
- missing expiry blocks execution
- stale lease blocks execution
- lease renewal requires new review
- lease renewal requires journal entry
- lease does not authorize execution by itself

## Safety Boundary

This module is advisory/read-only.

It does not issue leases, renew leases, execute commands, mutate runtime state, or approve remediation.
