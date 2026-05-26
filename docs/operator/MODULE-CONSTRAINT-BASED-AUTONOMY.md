# Module — Constraint-Based Autonomy

## Scope

Adds a read-only constraint surface for future autonomy decisions.

## Purpose

Define deterministic constraints that must be satisfied before any future autonomous action can be considered.

## Constraint Gates

- executor must be spot-core
- mode must be governed
- execution lease required
- review binding required
- backup binding required
- rollback binding required
- validation binding required
- immutable journal required
- worker self-apply forbidden
- high-risk network mutation approval-gated

## Safety Boundary

This module is advisory/read-only.

It does not execute, approve, remediate, mutate, restart, or change routing.
