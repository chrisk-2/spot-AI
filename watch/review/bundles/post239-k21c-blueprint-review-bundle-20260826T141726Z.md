# Post-2.39 K21C Installation and Activation Blueprint Review

## Review instruction

Worker-05 must return PASS, FIX, or NO for the K21C blueprint.

This review must not authorize installation, activation, scheduling,
production observation, remediation, service actions, or mutation.

## Repository identity

- repository head: `11850954445808e74e6c46007ce4c7961fcb04f2`
- generated UTC: `2026-08-26T14:17:27Z`

## Required PASS conditions

- installation and activation are separate promotion blocks
- installation leaves the observer inactive and disabled
- the first supervised observation is one-shot and exact-target only
- no timer is installed or authorized
- runtime and archive paths are fixed
- evidence uses replay-safe identities and exclusive creation
- backup, binding, verification, and rollback requirements are explicit
- service hardening and write boundaries are explicit
- arbitrary shell, targets, properties, URLs, and remote execution remain forbidden
- production observation requires a separate review and authorization
- execution_allowed remains false
- mutation_authority remains false

## Current governance

- implementation_present: true
- installation_authorized: false
- observer_installed: false
- observer_enabled: false
- observer_scheduled: false
- activation_authorized: false
- production_observation_authorized: false
- execution_allowed: false
- mutation_authority: false

## Current allowlist state

```json
{
  "activation_authorized": false,
  "authority": "read_only_observation_policy",
  "filesystem": {
    "approved_roots": [
      "/home/ogre/spot-stack/watch",
      "/home/ogre/spot-stack/docs",
      "/home/ogre/spot-stack/watch/state"
    ],
    "exact_files": [
      "/var/lib/spot/remediation-fixture/heartbeat.json"
    ],
    "operations": [
      "filesystem_metadata_read",
      "filesystem_bounded_content_read"
    ],
    "recursive_unbounded_traversal_allowed": false,
    "secret_collection_allowed": false,
    "special_files_allowed": false,
    "symlink_escape_allowed": false
  },
  "git": {
    "operations": [
      "git_status",
      "git_diff",
      "git_log",
      "git_show",
      "git_rev_parse",
      "git_branch_current"
    ],
    "repository": "/home/ogre/spot-stack"
  },
  "governance": {
    "execution_allowed": false,
    "live_executor_enabled": false,
    "mutation_authority": false,
    "network_mutation_allowed": false,
    "remediation_allowed": false,
    "remote_execution_allowed": false,
    "service_action_allowed": false
  },
  "host": "spot-core",
  "http": {
    "authentication_allowed": false,
    "endpoints": [
      "http://127.0.0.1:8787/health",
      "http://127.0.0.1:8787/fleet-status",
      "http://127.0.0.1:8010/health"
    ],
    "method": "GET",
    "query_strings_allowed": false,
    "redirects_allowed": false,
    "request_bodies_allowed": false
  },
  "implementation_present": true,
  "journal": {
    "follow_allowed": false,
    "mutation_allowed": false,
    "operation": "journal_read",
    "units_source": "systemd.units"
  },
  "limits": {
    "command_timeout_seconds_max": 15,
    "filesystem_content_bytes_max": 65536,
    "http_connect_timeout_seconds_max": 3,
    "http_total_timeout_seconds_max": 10,
    "journal_lines_max": 200,
    "journal_lookback_seconds_max": 3600,
    "output_bytes_max": 65536
  },
  "observer_enabled": false,
  "observer_installed": false,
  "observer_scheduled": false,
  "prohibited_classes": [
    "service_mutation",
    "process_signal",
    "package_mutation",
    "configuration_mutation",
    "permission_mutation",
    "network_mutation",
    "container_mutation",
    "remote_execution",
    "arbitrary_url_access",
    "credential_collection",
    "authority_mutation",
    "lease_mutation",
    "fence_mutation",
    "failover_mutation",
    "executor_activation",
    "automatic_remediation",
    "automatic_approval",
    "production_service_repair",
    "arbitrary_shell",
    "privilege_escalation",
    "interactive_execution"
  ],
  "schema": "spot_controlled_read_observe_allowlist_v1",
  "socket": {
    "fixed_invocation": [
      "ss",
      "-lntupH"
    ],
    "operations": [
      "socket_listening_read"
    ]
  },
  "status": "inactive",
  "systemd": {
    "global_operations": [
      "systemd_list_units",
      "systemd_list_unit_files"
    ],
    "unit_operations": [
      "systemd_show",
      "systemd_status",
      "systemd_is_active",
      "systemd_is_enabled"
    ],
    "units": [
      "spot-bridge-api.service",
      "spot-mcp.service",
      "spot-ui-publish.service",
      "starfleet-ui.service",
      "ttyd.service",
      "ssh.service",
      "docker.service",
      "spot-remediation-fixture.service",
      "spot-monitor-snapshot.service",
      "spot-primary-fence-guard.service",
      "spot-primary-lease-enforce.service",
      "spot-primary-lease-renew.service"
    ]
  },
  "version": 1
}
```

## K21A offline validation

```text
[PASS] baseline request and evidence accepted
[PASS] canonical request digest is deterministic
[PASS] canonical digest is key-order independent
[PASS] material request change alters digest
[PASS] byte-equivalent identity replay is deterministic
[PASS] rejected: same observation_id with changed payload
[PASS] rejected: same request_id with changed payload
[PASS] request minimum timeout accepted
[PASS] request maximum timeout accepted
[PASS] request minimum output bound accepted
[PASS] request maximum output bound accepted
[PASS] zero-byte evidence accepted
[PASS] maximum bounded evidence accepted
[PASS] maximum journal bounds accepted
[PASS] rejected: timeout below minimum
[PASS] rejected: timeout above maximum
[PASS] rejected: output bound below minimum
[PASS] rejected: output bound above maximum
[PASS] rejected: evidence timeout below minimum
[PASS] rejected: evidence timeout above maximum
[PASS] rejected: evidence output below minimum
[PASS] rejected: evidence output above maximum
[PASS] rejected: journal lines below minimum
[PASS] rejected: journal lines above maximum
[PASS] rejected: journal lookback below minimum
[PASS] rejected: journal lookback above maximum
deterministic_digest_tests=3
replay_tests=2
collision_tests=2
positive_bound_tests=7
negative_bound_tests=12
observer_implemented=true
observation_attempted=false
execution_attempted=false
execution_allowed=false
mutation_authority=false
live_executor_enabled=false
[PASS] complete K21A offline suite
```

## K21B offline validation

```text
[PASS] production execution surfaces absent
[PASS] default production path denied fail-closed
[PASS] offline fixture produced schema-valid evidence
[PASS] changed replay evidence rejected
[PASS] non-allowlisted service rejected without evidence write
pass=4 fail=0
observer_installed=false
observer_enabled=false
observer_scheduled=false
production_observation_performed=false
service_action_performed=false
execution_allowed=false
mutation_authority=false
RESULT: POST-2.39 K21B VALIDATION PASS
```

## Proposed K21C blueprint

# Post-2.39 K21C Controlled Read/Observe Installation and Activation Blueprint

## Status

DESIGN AND REVIEW ONLY

This blueprint does not authorize installation, activation, scheduling,
production observation, service actions, remediation, or mutation.

## Purpose

Define the exact promotion boundary between the accepted K21B dormant source
implementation and a future supervised, read-only production observation.

## Locked governance

- Spot Core remains the sole policy and execution authority.
- Worker self-apply remains prohibited.
- Worker-05 remains proposal/review only.
- `execution_allowed=false`
- `mutation_authority=false`
- `live_executor_enabled=false`
- `service_action_allowed=false`
- `remediation_allowed=false`
- `network_mutation_allowed=false`
- `remote_execution_allowed=false`
- Installation does not imply activation.
- Activation does not authorize remediation or mutation.
- A timer must not be installed during the first supervised observation.

## Promotion blocks

### K21C-1 — Blueprint review

Scope:

- review this installation and activation blueprint;
- verify exact paths, identities, boundaries, and rollback;
- perform no installation or production observation.

Exit gate:

- Worker-05 returns structured PASS;
- operator separately authorizes installation-only construction.

### K21C-2 — Installation-only construction

Repository artifacts to be constructed after authorization:

- `watch/observe/controlled-read-observe.service`
- `watch/observe/controlled-read-observe-install-validate.py`
- `watch/observe/controlled-read-observe-install-rollback.md`
- installation manifest schema and offline validator

Installation targets:

- runner:
  `/usr/local/lib/spot/observe/controlled-read-observe.py`
- shared validation module:
  `/usr/local/lib/spot/observe/controlled_read_observe_validation_v1.py`
- request validator:
  `/usr/local/lib/spot/observe/controlled-read-observe-request-validate.py`
- evidence validator:
  `/usr/local/lib/spot/observe/controlled-read-observe-evidence-validate.py`
- allowlist:
  `/etc/spot/observe/controlled-read-observe-allowlist-v1.json`
- request schema:
  `/etc/spot/observe/controlled-read-observe-request-schema-v1.json`
- evidence schema:
  `/etc/spot/observe/controlled-read-observe-evidence-schema-v1.json`
- systemd unit:
  `/etc/systemd/system/spot-controlled-read-observe.service`

Installation-only state:

- files may be installed only after separate authorization;
- the unit remains disabled and inactive;
- no timer is installed;
- no request is dispatched;
- no production evidence is created;
- `observer_installed=true` may be recorded only after identity verification;
- `observer_enabled=false`;
- `observer_scheduled=false`;
- `activation_authorized=false`.

### K21C-3 — First supervised observation

The first production observation requires another Worker-05 PASS and a new,
explicit operator authorization.

Exact first target:

- host: `spot-core`
- observation class: `systemd`
- operation: `systemd_show`
- target: `spot-remediation-fixture.service`
- execution mode: supervised one-shot
- timer or recurring schedule: forbidden

The observation may read only the fixed systemd properties already allowed by
the committed contracts. It must not start, stop, restart, reload, enable,
disable, mask, unmask, or otherwise change any service.

## Service design

Proposed unit identity:

- `spot-controlled-read-observe.service`
- `Type=oneshot`
- no `[Install]` section
- no automatic restart
- no timer dependency
- no network dependency
- fixed executable and configuration paths
- request supplied through one fixed root-owned request path
- evidence written beneath one fixed root-owned evidence directory

Required hardening:

- `User=root`
- `Group=root`
- `NoNewPrivileges=true`
- `PrivateTmp=true`
- `ProtectSystem=strict`
- `ProtectHome=true`
- empty capability bounding set
- `RestrictSUIDSGID=true`
- `LockPersonality=true`
- `MemoryDenyWriteExecute=true`
- filesystem write access limited to the evidence directory
- command timeout bounded by the committed allowlist

Root is required only for bounded read access. It does not grant mutation
authority.

## Runtime paths

Proposed request path:

`/var/lib/spot/controlled-read-observe/request.json`

Proposed evidence root:

`/var/lib/spot/controlled-read-observe/evidence`

Proposed immutable archive root:

`/mnt/collective/logs/spot/actions/post239-observe`

Requirements:

- request file must be root-owned and mode `0600`;
- runtime directory must be root-owned and mode `0700`;
- evidence files must use exclusive creation;
- existing evidence must never be overwritten;
- observation and request identities must be replay-safe;
- evidence must be schema-valid before acceptance;
- output remains bounded by the committed policy;
- secrets and credentials remain prohibited.

## Scheduling policy

K21C does not authorize recurring scheduling.

A future timer design requires its own review and authorization after the
first supervised one-shot observation passes.

Until then:

- timer unit absent;
- observer disabled;
- observer unscheduled;
- no automatic production observation.

## Backup requirements

Before installation, create and verify a backup manifest covering every
existing installation target.

For a missing destination, record:

- `missing_source=true`;
- intended installation path;
- reviewed source hash.

Installation is forbidden unless the backup manifest and binding validate.

## Rollback boundary

Rollback may affect only the K21C installation targets.

Rollback must:

1. stop only the observer unit if it is unexpectedly active;
2. restore every previously existing file from verified backup;
3. remove only files recorded as newly installed;
4. run `systemctl daemon-reload` only if the unit file changed;
5. verify the observer is absent or inactive, disabled, and unscheduled;
6. preserve all evidence and journals;
7. verify no unrelated service state changed.

Rollback execution requires explicit authority or may run automatically only
inside a separately reviewed installation transaction whose verification
fails.

## Required installation verification

- installed hashes equal reviewed source hashes;
- installed ownership and modes match the manifest;
- unit parses successfully;
- unit is inactive;
- unit is disabled;
- no timer exists;
- no request was dispatched;
- no production evidence was created;
- K21A and K21B offline regressions still pass;
- `execution_allowed=false`;
- `mutation_authority=false`.

## Required first-observation evidence

A future supervised observation receipt must correlate:

- operator authorization;
- Worker-05 PASS;
- reviewed bundle and SHA-256;
- repository commit;
- installation manifest;
- backup and rollback bindings;
- request digest;
- observation ID;
- evidence digest;
- exact target and operation;
- timeout and output bounds;
- validation result;
- final outcome.

## Explicitly forbidden by this blueprint

- installation without a separate authorization;
- enabling or scheduling the observer;
- timer creation during the first observation;
- arbitrary shell or command execution;
- arbitrary systemd properties;
- arbitrary host or service selection;
- remote execution;
- authenticated HTTP access;
- redirects or arbitrary URLs;
- service mutation;
- process signaling;
- package or configuration mutation;
- credential collection;
- remediation;
- production observation before separate authorization;
- widening `execution_allowed` or `mutation_authority`.

## Current state

- K21B implementation: accepted
- K21B implementation present: true
- K21C blueprint present: true after commit
- installation authorized: false
- observer installed: false
- observer enabled: false
- observer scheduled: false
- activation authorized: false
- production observation authorized: false
- execution allowed: false
- mutation authority: false
