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

## Collective-storage boot ordering

Docker containers bind-mount `/mnt/collective`, which is supplied through
the generated `mnt-collective.mount` CIFS unit. The managed Docker drop-in:

`/etc/systemd/system/docker.service.d/20-spot-collective-order.conf`

adds:

- `Wants=mnt-collective.mount`
- `After=mnt-collective.mount`

This makes Docker wait for the mount attempt before restoring containers.
`Wants` deliberately preserves the existing `nofail` behavior: failure of
the remote storage mount does not make Docker itself a required failure.

Installing the drop-in requires `systemctl daemon-reload` only. It does
not restart Docker or any running container.
