# Phase 12 — Advisory Learning Weights

## Status

Active lane after Phase 11 completion.

## Purpose

Phase 12 introduces advisory-only learning weights.

This phase lets Spot summarize historical fixture outcomes and produce routing/remediation recommendations without granting execution authority.

No mutation is authorized.

## Allowed

- read-only learning input ingestion
- advisory scoring
- confidence weighting
- recommendation generation
- deterministic learning reports
- immutable advisory journals
- rejection of self-authorizing recommendations

## Forbidden

- production mutation
- automatic execution
- config writes outside phase12/runs/
- worker role ownership changes
- routing changes
- firewall/DNS/DHCP/network mutation
- service restarts
- worker self-apply
- Codex mutation
- OpenAI mutation
- approval bypass

## Required invariants

- recommendations are advisory-only
- recommendations cannot approve themselves
- recommendations cannot mutate routing
- recommendations cannot change worker ownership
- recommendations cannot execute remediation
- confidence scores are deterministic
- all reports are journaled
- mutation_scope remains none

## Acceptance criteria

Phase 12 passes when validation proves:

- learning input ingestion
- deterministic advisory scoring
- confidence weighting
- recommendation generation
- self-approval blocked
- execution blocked
- routing mutation blocked
- worker ownership mutation blocked
- production target blocked
- journal records exist
- deterministic schema
- mutation scope none
