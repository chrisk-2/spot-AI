# Phase 2.39 Restricted Service Executor

## Block C scope

Block C establishes a dormant, exact-allowlist service executor contract.

It does not authorize or perform service repair.

## Exact allowlist

- Executor host: `spot-core`
- Service: `spot-remediation-fixture.service`
- Read-only operation: `diagnose`
- Recognized but blocked operation: `repair`

No additional host, service, operation, command, systemctl property, or remote
execution target is accepted.

## Diagnostic interface

The only production subprocess interface is a fixed argument-vector invocation
of `systemctl show`.

The executable, operation, property set, and service name are constants.
No shell is used.

## Repair interface

The `repair` operation is intentionally dormant and fails closed with:

- `execution_allowed=false`
- `mutation_authority=false`
- `live_executor_enabled=false`
- `service_action_performed=false`
- `service_restart_performed=false`
- `production_service_mutation=false`

## Validation isolation

The validator enables `SPOT_RESTRICTED_EXECUTOR_VALIDATION=1`.

In that mode, diagnosis uses a built-in immutable fixture and does not invoke
`systemctl`. Validation cannot supply a command, executable, unit property, or
alternate fixture file.

## Explicit exclusions

Block C does not:

- restart, start, stop, reload, enable, or disable a service;
- invoke `sudo`;
- use a shell;
- use SSH or remote execution;
- accept arbitrary commands;
- accept arbitrary systemd units or properties;
- bind a backup or rollback artifact;
- create execution authority;
- permit worker self-application;
- integrate a live repair path into the operator.
