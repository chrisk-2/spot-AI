# Phase 13 — Supervised Operational Intelligence Fabric

## Status

Active lane after Phase 12 completion.

## Purpose

Phase 13 aggregates observation, planning, execution proof, rollback proof, chain orchestration, and advisory learning into a supervised operational intelligence fabric.

This phase produces an intelligence envelope only.

No production mutation is authorized.

## Allowed

- read-only observation summary intake
- dry-run remediation plan summary intake
- fixture execution proof summary intake
- rollback proof summary intake
- supervised chain proof summary intake
- advisory learning summary intake
- governed intelligence envelope generation
- readiness classification
- operator recommendation generation

## Forbidden

- autonomous production mutation
- autonomous service restart
- routing mutation
- worker ownership mutation
- firewall/DNS/DHCP/network mutation
- Codex mutation
- OpenAI mutation
- worker self-apply
- approval bypass
- backup bypass
- rollback bypass

## Required invariants

- intelligence output is advisory only
- execution_allowed is false
- approval_allowed is false
- mutation_scope is none
- routing_change_allowed is false
- worker_ownership_change_allowed is false
- production_mutation_allowed is false
- readiness may recommend next phase but cannot authorize it

## Acceptance criteria

Phase 13 passes when validation proves:

- fabric input aggregation
- readiness classification
- advisory recommendation generation
- no execution authority
- no approval authority
- no routing mutation authority
- no worker ownership authority
- no production mutation authority
- missing proof blocks readiness
- failed proof blocks readiness
- deterministic schema
- immutable fabric journal
- mutation scope none
