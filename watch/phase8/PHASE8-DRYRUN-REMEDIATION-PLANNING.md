# Phase 8 — Dry-Run Remediation Planning

## Status

Active lane after Phase 7 completion.

## Purpose

Phase 8 introduces deterministic dry-run remediation planning against approved observation findings.

This phase allows Spot to generate governed remediation proposals without execution authority.

No live mutation is authorized.

## Allowed

- remediation proposal generation
- deterministic remediation classification
- dry-run execution simulation
- rollback planning
- backup planning
- validation planning
- proposal journaling
- approval requirement classification

## Forbidden

- production mutation
- config writes outside phase8/runs/
- service restart execution
- firewall/DNS/network mutation
- autonomous apply
- worker self-apply
- Codex mutation
- OpenAI mutation
- rollback execution
- backup execution

## Required invariants

- all plans are proposal-only
- all plans require approval state
- all plans include rollback definition
- all plans include backup definition
- all plans include validation definition
- all plans remain replay-safe
- all plans remain deterministic
- no execution path exists

## Risk classes

- low
- medium
- high
- forbidden

## Acceptance criteria

Phase 8 passes when validation proves:

- deterministic proposal generation
- remediation classification
- forbidden action rejection
- rollback planning presence
- backup planning presence
- validation planning presence
- approval gating
- replay-safe proposal identity
- immutable proposal journals
- proposal-only mutation scope
