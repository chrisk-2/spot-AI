# Module — Adaptive Scheduling Intelligence

## Scope

This module adds read-only advisory scheduling recommendations.

## Added

- watch/scheduling/adaptive-scheduling-snapshot.py
- watch/scheduling/adaptive-scheduling-validate.py
- operator command: scheduling-advice
- operator command: scheduling-validate

## Inputs

- capability registry
- routing confidence scores
- worker eligibility
- quarantine state
- installed models
- warm models
- confidence bands

## Safety Boundary

This module is advisory only.

It does not:
- change routing
- change worker ownership
- move models
- quarantine workers
- unquarantine workers
- execute tasks
- authorize mutation

## Policy

Scheduling advice is informational only.
Locked owner routing remains authoritative.
Mutation authority remains false.
Spot Core remains sole executor.
