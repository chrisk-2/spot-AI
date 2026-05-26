# Module — Fleet Capability Registry Normalization

## Scope

This module adds a read-only normalized capability registry for Starfleet workers.

## Added

- watch/capabilities/capability-registry-snapshot.py
- watch/capabilities/capability-registry-validate.py
- operator command: capabilities
- operator command: capabilities-validate

## Normalized Fields

- worker
- ip
- base_url
- primary_role
- secondary_roles
- routing_enabled
- eligible
- quarantined
- configured models
- installed models
- warm models
- alerts

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
- change routing ownership
- change worker roles
- change models
- quarantine or unquarantine workers
- restart services
- modify cluster config

## Policy

Capability visibility supports routing and operator decisions only.
Mutation authority remains false.
Spot Core remains the sole executor.
