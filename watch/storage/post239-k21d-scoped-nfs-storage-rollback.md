# POST-2.39 K21D Scoped NFS Storage Rollback

Status: implementation contract; execution requires the transaction-bound authorization.

## Scope

Rollback affects only these units and their exact installed files:

- `mnt-collective-backups-spot\x2dcore-post239\x2dk21d.mount`
- `mnt-collective-logs-spot-actions-post239\x2dk21d.mount`

It must not alter `/etc/fstab`, the parent `/mnt/collective` CIFS mount, Docker, the original CIFS records, or any K21D live installation destination.

## Automatic rollback order

1. Stop and disable the two scoped mount units if they were started or enabled by the transaction.
2. Confirm neither fixed target remains a mount point.
3. Remove an installed unit file only when its SHA-256 still equals the reviewed template SHA-256.
4. Reload the systemd manager only when a unit file was removed.
5. Verify the parent `/mnt/collective` view remains CIFS from `//unimatrix6/docker`.
6. Verify the original K21D manifest and transaction become visible with their approved SHA-256 values.
7. Verify Docker retains its pre-transaction main PID and active-enter timestamp.
8. Retain all pre-change backup artifacts, backup bindings, NFS-created directories, and NFS record copies.
9. Write an exclusive failure receipt describing every rollback result.

## Fail-closed rules

- Never delete or overwrite the NFS copies during automatic rollback.
- Never remove a unit file whose content changed after installation.
- Never claim rollback success while either scoped target remains mounted.
- Never restart Docker.
- Never consume or reuse the revoked K21D installation authorization.
- Never install, start, enable, schedule, or invoke the K21D observer.
- Any incomplete rollback requires operator inspection before another transaction.

`execution_allowed=false`

`mutation_authority=false`
