# Phase 15 — Operator Approval Token Gate

## Status

Active lane after Phase 14 completion.

## Purpose

Phase 15 creates a deterministic operator approval token gate.

This phase proves that even when a production-readiness candidate is ready for operator review, execution remains blocked unless a valid operator approval token exists.

This phase does not execute production actions.

## Allowed

- approval token schema validation
- approval token binding to candidate ID
- approval expiry validation
- approval scope validation
- approval journal generation
- denial journal generation
- readiness-to-approval handoff validation

## Forbidden

- production mutation
- service restart execution
- config writes outside phase15/runs/
- network/firewall/DNS/DHCP/routing mutation
- worker self-apply
- Codex mutation
- OpenAI mutation
- approval fabrication
- approval bypass
- backup bypass
- rollback bypass

## Required approval token fields

- schema
- approval_id
- candidate_id
- approved_by
- approval_scope
- approved_at
- expires_at
- approved_action
- approved_target
- operator_confirmed

## Acceptance criteria

Phase 15 passes when validation proves:

- valid approval token accepted for review handoff
- missing approval token blocks
- expired approval token blocks
- candidate mismatch blocks
- target mismatch blocks
- action mismatch blocks
- scope mismatch blocks
- missing operator confirmation blocks
- non-operator approver blocks
- execution authority remains blocked
- deterministic schema
- approval journal exists
- denied journal exists
- mutation scope none
