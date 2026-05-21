# Unified Governance Event Schema

Purpose: normalize Spot runtime, review, queue, lease, routing, backup, rollback, validation, and journal events into one read-only event envelope.

Schema version: spot.governance.event.v1

Authority invariants:
- executor is always spot-core
- mutation_authority is always false
- worker_self_apply_allowed is always false
- normalized events do not authorize execution

Primary fields:
- event_id
- ts
- event_type
- authority
- source
- correlation
- subject
- decision
- metrics
- raw_ref
- integrity

Operator commands:
- watch/runtime/spot-governance-event-normalize.py --limit 100
- watch/runtime/spot-governance-event-normalize.py --limit 100 --summary
- watch/runtime/spot-governance-event-normalize.py --limit 100 | watch/runtime/spot-governance-event-validate.py

This lane is read-only normalization. It does not alter execution, review, backup, rollback, or approval gates.
