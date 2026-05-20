# Runtime Metrics Model

Scope: read-only.

Purpose:
- aggregate runtime governance signals into one deterministic metrics snapshot
- expose queue, routing, governance, archive, and validation health
- support future UI/API integration without adding execution authority

Authority:
- no mutation
- no service restart
- no queue transition
- no review verdict change
- no routing ownership change
- no archive write/delete

Inputs:
- watch/runtime/queue/runs/
- watch/state/routing-audit.jsonl
- /mnt/collective/logs/spot/
- validation output artifacts when present

Outputs:
- metrics JSON snapshots under watch/runtime/metrics/runs/
- read-only summary text

Safety:
- missing inputs produce warnings, not mutation
- malformed optional inputs are counted and reported
- no production target action is possible from this lane
