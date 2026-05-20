# Runtime Queue Persistence Model

Scope: fixture/simulation only.

Purpose:
- persist queue candidates to disk
- prevent replay execution
- preserve immutable receipts
- recover safely after restart

Authority:
- no production mutation
- no service restart authority
- no routing ownership mutation
- Spot Core remains sole executor

Queue state:
- pending
- leased
- completed
- denied
- expired

Required guarantees:
- deterministic candidate IDs
- one active lease per candidate
- immutable receipt per transition
- replay blocked after terminal state
- stale leases recover to pending or expired by policy
