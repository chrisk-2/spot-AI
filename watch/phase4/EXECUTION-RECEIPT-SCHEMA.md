# Phase 4 — Execution Receipt Schema

## Purpose

Define immutable execution receipts for controlled noop executor testing.

## Required Fields

JSON shape:

    {
      "receipt_id": "string",
      "created_at": "utc-iso8601",
      "request_id": "string",
      "execution_id": "string",
      "lease_id": "string",
      "phase": "4",
      "executor": "spot-core",
      "action_type": "noop",
      "target": "string",
      "risk_class": "none|low|medium|high",
      "mutation_performed": false,
      "execution_performed": true,
      "noop_performed": true,
      "rollback_required": false,
      "rollback_performed": false,
      "kill_switch_checked": true,
      "final_outcome": "success|blocked|failed"
    }

## Invariants

- receipt_id must be deterministic from request_id, execution_id, lease_id, and action_type
- receipts are append-only artifacts
- receipts must not be overwritten
- mutation_performed must remain false in Phase 4
- rollback_performed must remain false in Phase 4
