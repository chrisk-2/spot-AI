# Phase 28 — Capability Registry Enforcement

Status: DESIGN-ONLY

## Purpose

Define future enforcement of declared worker capabilities.

## Enforcement Direction

Future execution gates must verify:

- requested role
- declared worker capability
- allowed action class
- allowed target scope
- prohibited authority escalation

## Forbidden Behavior

- worker self-apply
- undeclared capability execution
- routing ownership mutation
- hidden execution authority
- model/provider approval as execution authority

Spot Core remains sole executor.
