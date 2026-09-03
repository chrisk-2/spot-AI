# POST-2.39 K21D Scoped NFS Storage Design

Status: DESIGN ONLY — EXECUTION NOT AUTHORIZED

## Selected boundary

K21D will use two direct NFSv4 subdirectory mounts while retaining the existing `/mnt/collective` CIFS mount.

| Purpose | NFS source | Fixed target |
|---|---|---|
| Backup | `192.168.50.10:/volume1/spotvault/backups/spot-core/post239-k21d` | `/mnt/collective/backups/spot-core/post239-k21d` |
| Evidence | `192.168.50.10:/volume1/spotvault/logs/spot/actions/post239-k21d` | `/mnt/collective/logs/spot/actions/post239-k21d` |

Planned mount options:

`rw,vers=4.0,proto=tcp,hard,timeo=600,retrans=2,sec=sys,nosuid,nodev,noexec,noatime,_netdev`

## Systemd units

- `mnt-collective-backups-spot\x2dcore-post239\x2dk21d.mount`
- `mnt-collective-logs-spot-actions-post239\x2dk21d.mount`

Both units must depend on the parent `/mnt/collective` mount and `network-online.target`.

## Migration contract

1. Preserve the original CIFS records.
2. Create the two scoped NFS source directories with `0700 root:root`.
3. Copy records without overwriting any existing NFS object.
4. Preserve and verify the approved SHA-256 values.
5. Store record files as `0400 root:root`.
6. Store the backup files directory as `0700 root:root`.
7. Activate only the two scoped mounts.
8. Do not restart Docker.
9. Do not install or activate K21D during storage correction.

## Rollback contract

Rollback stops and removes only the two scoped mount units. The original CIFS records then become visible again. NFS copies are retained as evidence and are not deleted automatically.

## Governance

The prior K21D installation authorization remains revoked and unconsumed. This design grants no execution authority. Independent review and a new single-use authorization are required before storage mutation.

`execution_allowed=false`

`mutation_authority=false`
