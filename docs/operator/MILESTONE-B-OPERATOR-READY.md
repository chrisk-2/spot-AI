# Milestone B — Operator Ready

## Purpose

Standardize safe operator entry points for Spot without changing runtime authority.

## Entry Point

Primary command:

watch/operator/spot-operator.sh <command>

## Commands

- status  : read-only
- routing : read-only
- audit   : read-only
- review  : validation-only
- validate: validation-only
- smoke   : validation-only
- dirty   : read-only

## Safety Boundaries

- No worker self-apply.
- No mutation authority is added.
- No backup/review/rollback bypass exists.
- OpenAI/Codex remain proposal/review only.
- Runtime state remains separate from source-of-truth config.
- starfleet-ui/public/status.json is excluded from this lane.

## Acceptance Criteria

- smoke validation PASS
- normal validation PASS
- governance integrity PASS
- only unrelated dirty file:
  M starfleet-ui/public/status.json
