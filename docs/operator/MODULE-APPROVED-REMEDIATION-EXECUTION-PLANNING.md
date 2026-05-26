# Module — Approved Remediation Execution Planning

## Scope

Adds read-only planning for future approved remediation execution.

## Purpose

Define the required structure for a remediation plan before any future execution path can be considered.

## Required Plan Bindings

- request id
- target
- service
- risk class
- execution lease
- review verdict
- backup binding
- rollback binding
- validation command
- journal target
- approval marker when policy requires it

## Safety Boundary

This module is advisory/read-only.

It does not:

- execute remediation
- restart services
- write configs
- create live backups
- perform rollback
- mutate runtime state
- approve its own plan

## Authority

Spot Core remains the only possible executor.
Workers, Codex, OpenAI, and reviewers remain non-executors.
