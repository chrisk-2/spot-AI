# Module — Replay-Safe Execution Token Model

## Scope

Adds a read-only replay-safe execution token model.

## Purpose

Define the token constraints required before any future governed executor call can be considered replay-safe.

## Required Token Fields

- token id
- request id
- action id
- executor
- target
- service
- risk class
- lease id
- review id
- backup binding id
- rollback binding id
- receipt id
- issued at
- expires at
- nonce
- token scope
- journal path

## Safety Boundary

This module is advisory/read-only.

It does not:

- issue live execution tokens
- execute commands
- mutate runtime state
- approve remediation
- bypass review, backup, rollback, lease, receipt, validation, or approval gates

## Authority

Spot Core remains sole executor.
A token model proves required replay controls; it does not authorize action.
