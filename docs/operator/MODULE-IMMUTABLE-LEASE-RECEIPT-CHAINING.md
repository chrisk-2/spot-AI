# Module — Immutable Lease Receipt Chaining

## Scope

Adds a read-only immutable lease receipt chaining model.

## Purpose

Define deterministic chain continuity between:

- execution lease
- replay token
- approval chain
- rollback binding
- execution receipt
- recovery receipt

## Required Chain Fields

- chain id
- parent receipt id
- lease id
- replay token id
- approval id
- rollback binding id
- execution receipt id
- recovery receipt id
- chain status
- integrity hash
- journal path
- timestamp

## Chain Rules

- broken chain blocks execution completion
- orphan receipt blocks execution completion
- receipt ordering required
- replay token must match lease
- approval chain must match receipt
- rollback binding must match receipt
- integrity hash mismatch blocks completion
- append-only chain required

## Safety Boundary

This module is advisory/read-only.

It does not:

- execute commands
- generate live hashes
- mutate runtime state
- approve execution
- bypass governance

## Authority

Spot Core remains sole executor.
Receipt chaining validates continuity; it does not authorize execution.
