# Post-2.39 Controlled Read/Observe Lane Design

## Status

Design only.

This document does not activate an executor, authorize production mutation, grant
mutation authority, or change `execution_allowed`.

The accepted Phase 2.39 boundary remains intact.

## Purpose

Define a tightly bounded production-adjacent observation capability for Spot Core.

The lane may collect diagnostic evidence from explicitly permitted local targets.
It may report conditions and recommend separately reviewed work. It may not repair,
restart, reconfigure, install, remove, enable, disable, or otherwise mutate anything.

## Authority Boundary

Spot Core remains the sole policy and execution authority.

For this design:

- `execution_allowed=false`
- `mutation_authority=false`
- `live_executor_enabled=false`
- remote execution is forbidden
- production mutation is forbidden
- authority-state mutation is forbidden
- observation cannot automatically escalate into remediation

A failed observation must fail closed and produce no corrective action.

## Permitted Host

Only the local host:

- `spot-core`

No SSH, remote shell, remote systemd, remote HTTP, fleet sweep, subnet discovery,
SNMP walk, or unbounded target discovery is permitted.

## Permitted Systemd Units

Read-only metadata and bounded journals may target only:

- `spot-bridge-api.service`
- `spot-mcp.service`
- `spot-ui-publish.service`
- `starfleet-ui.service`
- `ttyd.service`
- `ssh.service`
- `docker.service`
- `spot-remediation-fixture.service`
- `spot-monitor-snapshot.service`
- `spot-primary-fence-guard.service`
- `spot-primary-lease-enforce.service`
- `spot-primary-lease-renew.service`

The presence of a unit on this list does not authorize starting, stopping, restarting,
reloading, enabling, disabling, masking, unmasking, or resetting it.

Other units, including the observed failed `glpi-agent.service`, are outside this
initial lane. Their state may not trigger repair through this contract.

## Permitted Systemd Operations

Only these read-only operations are candidates for later implementation:

- `systemctl show UNIT`
- `systemctl status UNIT --no-pager`
- `systemctl is-active UNIT`
- `systemctl is-enabled UNIT`
- `systemctl list-units --type=service`
- `systemctl list-unit-files --type=service`

Every unit-specific operation must resolve to an exact allowlisted unit.

Wildcards, templates supplied by callers, partial names, shell expansion, and
caller-controlled command fragments are forbidden.

## Permitted Journal Operations

Journal inspection must:

- specify exactly one allowlisted unit
- use `--no-pager`
- use a fixed maximum line count
- use a fixed recent time boundary
- exclude follow mode
- exclude vacuuming, rotation, flushing, or namespace mutation
- return bounded output
- enforce a timeout

Candidate form:

`journalctl --unit UNIT --since TIME --lines COUNT --no-pager`

`UNIT`, `TIME`, and `COUNT` must be validated against fixed policy limits before use.

## Permitted Socket Inspection

Local listening-socket inspection may use a fixed read-only invocation equivalent to:

`ss -lntupH`

No socket manipulation, packet transmission, namespace changes, or remote probing is
authorized.

## Permitted Local HTTP Reads

Only HTTP `GET` requests to explicitly allowlisted loopback endpoints may be considered.

Initial endpoint candidates:

- `http://127.0.0.1:8787/health`
- `http://127.0.0.1:8787/fleet-status`
- `http://127.0.0.1:8010/health`

Requirements:

- method must be `GET`
- redirects must be disabled
- hostname must resolve literally to `127.0.0.1` or `localhost`
- port and path must exactly match the allowlist
- query strings are forbidden
- request bodies are forbidden
- authentication material is forbidden
- connection and total timeouts are mandatory
- response size must be bounded
- non-allowlisted URLs fail closed

Endpoint existence and response contracts require a later read-only verification step.
This design does not call them.

## Permitted Filesystem Inspection

A future implementation may read metadata or bounded content only from separately
approved exact paths.

Initial path classes:

- repository control documents under `/home/ogre/spot-stack/watch`
- repository operator documents under `/home/ogre/spot-stack/docs`
- governance state under `/home/ogre/spot-stack/watch/state`
- fixture heartbeat at `/var/lib/spot/remediation-fixture/heartbeat.json`

Requirements:

- canonical path resolution
- exact root enforcement
- no symlink escape
- no device, socket, FIFO, or executable invocation
- bounded file size
- no recursive unrestricted traversal
- no secret, credential, key, token, or environment-file collection
- no writes, ownership changes, permission changes, or timestamp changes

## Permitted Repository Inspection

Only non-mutating Git operations may be considered:

- `git status`
- `git diff`
- `git log`
- `git show`
- `git rev-parse`
- `git branch --show-current`

Forbidden Git operations include staging, committing, pushing, pulling, fetching,
switching, restoring, resetting, cleaning, merging, rebasing, and modifying refs.

## Evidence Contract

Every completed observation must produce a bounded evidence record containing:

- schema version
- observation ID
- request or correlation ID
- timestamp in UTC
- hostname
- observer identity
- observation class
- exact allowlisted target
- normalized operation
- start and completion timestamps
- timeout applied
- exit status or HTTP status
- output byte count
- output truncation indicator
- SHA-256 digest of captured output
- classification: healthy, degraded, failed, or unknown
- policy decision
- `execution_allowed=false`
- `mutation_authority=false`
- `live_executor_enabled=false`
- `remediation_performed=false`
- `service_action_performed=false`
- `network_stack_mutation=false`

Evidence creation must not overwrite an existing record. Observation identifiers must
be replay-safe. A duplicate identity with different content must fail closed.

## Required Output Controls

Future implementation must enforce:

- fixed timeouts
- fixed output-size limits
- bounded journal lines
- bounded filesystem reads
- structured output
- sensitive-value redaction
- no arbitrary shell evaluation
- no caller-provided environment variables
- no command substitution
- no privilege escalation
- no interactive mode

## Explicitly Prohibited Operations

This lane may never perform:

- service start, stop, restart, reload, enable, disable, mask, or unmask
- process termination or signaling
- package installation, removal, upgrade, or repository changes
- configuration-file creation or modification
- permission or ownership changes
- firewall, DNS, route, address, link, VLAN, tunnel, or interface mutation
- container start, stop, restart, creation, deletion, or image mutation
- remote execution
- arbitrary URL access
- credential collection
- authority, lease, fence, or failover mutation
- executor activation
- automatic remediation
- automatic approval
- production service repair

## Failure Behavior

Any invalid target, unknown operation, timeout, oversized response, malformed output,
policy mismatch, path escape, unexpected redirect, or evidence-write conflict must:

1. terminate the observation
2. classify the result as failed or unknown
3. preserve all governance locks
4. perform no retry that could cause mutation
5. produce no remediation request automatically
6. require separate operator review for any follow-up

## Required Successor Gates

Before implementation or activation, a separate reviewed block must provide:

1. machine-readable target and operation allowlists
2. schema and validator for observation requests
3. schema and validator for evidence receipts
4. negative tests for every prohibited class
5. replay and collision tests
6. timeout and output-bound tests
7. path-escape and URL-bypass tests
8. W-5 grounded review
9. explicit operator authorization
10. proof that all execution and mutation locks remain false

## Acceptance Boundary

Completion of this document means only that the initial read/observe lane is designed.

It does not mean:

- the lane is implemented
- the lane is validated
- the lane is activated
- a health endpoint was called
- a service was changed
- a repair was attempted
- production autonomy was expanded
