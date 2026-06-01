# spot-worker-04 Recovery Runbook

## Scope

Recovery procedure reference for spot-worker-04.

## Recovery Source

- verified backup
- recovery manifest
- recovery readiness framework

## Validation

- hostname verified
- ssh operational
- mounts active
- role ownership preserved
- required services active
- fleet validation pass

## Governance

- Spot Core remains sole executor
- no worker self-apply
- no backup means no change
- no rollback means no execution

## Status

Design-only reference.
