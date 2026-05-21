# Governance Event API

Endpoint:

GET /stats/runtime/governance-events?limit=100

Purpose:
Expose normalized governance events through Spot Core as read-only API telemetry.

Authority:
- read-only only
- mutation_authority false
- executor remains spot-core
- no review, backup, rollback, approval, or execution gate is bypassed

Source:
watch/runtime/spot-governance-event-normalize.py
