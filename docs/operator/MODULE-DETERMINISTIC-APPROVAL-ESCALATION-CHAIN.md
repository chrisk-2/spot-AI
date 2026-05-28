# Module — Deterministic Approval Escalation Chain

## Scope

Adds a read-only approval escalation chain model.

## Purpose

Define deterministic approval requirements for future governed execution paths.

## Approval Chain Inputs

- request id
- action id
- target
- service
- risk class
- review verdict
- execution lease id
- backup binding id
- rollback binding id
- execution window id
- replay token id
- receipt id
- approval status
- approval authority
- journal path

## Escalation Rules

- low risk may proceed only after required deterministic gates
- medium risk requires policy allowlist or approval
- high risk requires explicit approval
- network/firewall/DNS/DHCP/VLAN/SSH changes require explicit approval
- reviewers cannot approve their own generated work
- workers cannot approve execution
- OpenAI cannot approve execution
- Codex cannot approve execution
- Spot Core enforces but does not invent approval

## Safety Boundary

This module is advisory/read-only.

It does not approve, execute, mutate, restart, schedule, or bypass governance.
