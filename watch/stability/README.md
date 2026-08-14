# SPOT Core Seven-Day Stability Observer

Purpose: prove that SPOT Core remains stable for seven continuous days
without unexplained container, Docker, MCP, or Bridge restarts.

The observer is read-only with respect to operational services. It may
write only its evidence under:

`/var/lib/spot/stability-soak`

Observed conditions include:

- Spot Core container identity and restart count
- Docker daemon restart count
- MCP and Bridge service state and restart count
- Spot Core and Bridge endpoint availability
- `/mnt/collective` availability
- primary fencing and witness-lease state
- `execution_allowed=false`
- `mutation_authority=false`
- automatic takeover disabled

Status values:

- `SOAKING`: observation window active with no failures
- `FAIL`: one or more failure samples recorded
- `PASS`: seven days elapsed with zero failure samples

The observer never restarts services, recreates containers, changes network
configuration, enables execution, or grants mutation authority.
