# Module — Runtime Observability Polish

## Scope

This module adds a read-only runtime observability snapshot and validator.

## Added

- watch/runtime/observability/runtime-observability-snapshot.py
- watch/runtime/observability/runtime-observability-validate.py
- operator command: runtime-snapshot
- operator command: runtime-validate

## Required Runtime Sources

- health
- fleet ping
- routing
- routing audit
- governance events

## Optional Runtime Sources

- runtime journals
- review lease telemetry
- queue metrics

Optional sources are collected when available but do not block validation.

## Safety Boundary

This module is read-only.

It does not:
- restart services
- modify config
- modify runtime state
- write governance records
- authorize execution
- bypass review, backup, or rollback gates

## Policy

Runtime observability supports operator inspection only.
Mutation authority remains false.
Spot Core remains the sole executor.
