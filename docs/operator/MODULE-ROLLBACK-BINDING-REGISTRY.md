# Module — Rollback Binding Registry

## Scope

Adds a read-only rollback binding registry model.

## Purpose

Define the required rollback binding fields for any future governed execution path.

## Required Rollback Binding Fields

- rollback binding id
- request id
- action id
- target
- service
- risk class
- backup binding id
- rollback strategy
- rollback command or procedure reference
- rollback validation command
- rollback halt condition
- journal path
- timestamp

## Safety Boundary

This module is advisory/read-only.

It does not:

- execute rollback
- restore files
- restart services
- mutate runtime state
- authorize execution
- bypass review, backup, lease, validation, receipt, or approval gates

## Authority

Spot Core remains sole executor.
Rollback binding proves rollback is defined; it does not authorize action.
