# Review Lease Telemetry

Read-only runtime telemetry for:
- review latency
- review verdict distribution
- lease ownership visibility
- runtime telemetry correlation

## Endpoint

GET /stats/runtime/review-lease

## Authority Boundary

- read-only only
- no mutation authority
- Spot Core remains sole executor
- no backup/review/rollback bypass
