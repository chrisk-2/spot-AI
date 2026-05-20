# Phase 6 — Governed Fixture Apply Queue

## Purpose

This file defines the remaining Phase 6 completion lane after the initial fixture-service orchestration proof.

## Scope

The apply queue is fixture-only. It does not authorize production service mutation.

## Queue lifecycle

Valid queue states:

- pending
- approved
- rejected
- dispatched
- blocked
- rolled_back

## Required gates

A queued operation may dispatch only when:

- target is fixture-service
- executor is spot-core
- queue state is approved
- backup_id is present
- rollback_id is present
- validation_id is present
- execution lease is valid
- action is fixture-scoped
- replay guard has not seen the execution identity

## Required blocks

The queue must block:

- pending dispatch
- rejected dispatch
- worker executor dispatch
- missing backup
- missing rollback
- missing validation
- expired lease
- replayed execution identity
- target escape

## Completion

Phase 6 is complete when full validation proves:

- fixture lifecycle orchestration
- supervised state transitions
- governed apply queue
- backup/rollback/validation gate enforcement
- rollback continuity
- lease expiration blocking
- replay guard blocking
- target escape blocking
- worker self-apply blocking
- fixture-only mutation scope
