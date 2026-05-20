# Phase 4 — Kill-Switch Invariants

## Purpose

Define mandatory kill-switch behavior before any executor path becomes live.

## Required Behavior

- executor checks kill-switch before action
- disabled state blocks execution
- missing kill-switch state blocks execution
- unreadable kill-switch state blocks execution
- kill-switch result is recorded in receipt

## Phase 4 Rule

Even noop execution must be blocked if the kill-switch is not explicitly permissive.

## Forbidden

- default allow
- silent bypass
- worker override
- model override
- OpenAI override
