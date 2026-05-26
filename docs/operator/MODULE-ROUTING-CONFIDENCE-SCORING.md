# Module — Routing Confidence Scoring

## Scope

This module adds read-only routing confidence scoring.

## Added

- watch/routing/routing-confidence-snapshot.py
- watch/routing/routing-confidence-validate.py
- operator command: routing-confidence
- operator command: routing-confidence-validate

## Confidence Inputs

- worker health
- eligibility
- quarantine state
- alerts
- latency
- fallback count
- locked role ownership

## Locked Role Ownership

- general -> spot-worker-01
- utility -> spot-worker-02
- coding -> spot-worker-03
- heavy -> spot-worker-04
- review -> spot-worker-05
- reasoning -> spot-worker-06

## Safety Boundary

This module is read-only.

It does not:
- change routing
- change worker roles
- quarantine workers
- unquarantine workers
- restart services
- modify cluster config
- authorize execution

## Policy

Routing confidence is advisory only.
Mutation authority remains false.
Spot Core remains sole executor.
