# Post-2.39 Controlled Read/Observe Gate Review Bundle

## Review request

Worker-05 must review the inactive read-only observation contracts.
Return PASS, FIX, or NO. Do not authorize implementation or activation.

## Repository identity

- repository head: `2835caa80d3fcd48354bb5a9558518aa2686dc8c`
- generated UTC: `2026-08-26T13:40:48Z`

## Required PASS conditions

- allowlists are exact and machine-readable
- request and evidence schemas fail closed
- prohibited targets and operations are rejected
- replay identities and collisions are controlled
- timeout, journal, and output bounds are enforced
- path escape and URL bypass are rejected
- no observer implementation is present
- no production observation is performed
- Spot Core remains sole authority
- Worker-05 remains proposal_review_only
- execution_allowed remains false
- mutation_authority remains false

## Validation result

- K21A offline suite: PASS
- deterministic digest tests: 3
- replay tests: 2
- collision tests: 2
- positive bound tests: 7
- negative bound tests: 12
- production observations: 0
- execution attempts: 0

## Reviewed artifact hashes

```text
c54f8629ab9ab2d91cba81d6f6fcd26fedc853c5c009494891b859e09162da5c  watch/observe/POST239-CONTROLLED-READ-OBSERVE-LANE-DESIGN.md
cd80676c4a5c0e50e8e4c347cb44de1935e66c5d9869d74062163b97265af7d6  watch/observe/controlled-read-observe-allowlist-v1.json
bfc9f80a244d5021858d49d7693f15f4f32b07af0dd5fe2675c0b666306cd78b  watch/observe/controlled-read-observe-request-schema-v1.json
9f11ed5b354e8f964ac2317155869dc67fec9e558d5223f12cb233adc5d6607d  watch/observe/controlled-read-observe-evidence-schema-v1.json
6ace18174fd7dcd5ce1c563d084eed338040254053d683a6220bde5b446e4667  watch/observe/controlled-read-observe-request-validate.py
c18ba77dbcfbda0649ec6a3aa83ef0a2991dd18e1cfbf2b179cecde18e3f02b8  watch/observe/controlled-read-observe-evidence-validate.py
5088b6ce5365c272e96846d3ae3e1c8b4cbe075369cc1fac313995bf8f116a7a  watch/observe/controlled-read-observe-replay-bounds-validate.py
8d28f43d7dcf66464f9f67a912c1f2d528dbb8b827989e1782d632be738c7074  watch/observe/controlled_read_observe_validation_v1.py
```

## Governance boundary

- observer status: inactive
- implementation_present: false
- activation_authorized: false
- observer_installed: false
- observer_enabled: false
- observer_scheduled: false
- execution_allowed: false
- mutation_authority: false
- live_executor_enabled: false
- remediation_allowed: false
- service_action_allowed: false
- remote_execution_allowed: false

## Required response

```json
{
  "verdict": "PASS|FIX|NO",
  "execution_allowed": false,
  "confidence": "high|medium|low",
  "intent_match": "pass|fail",
  "policy_match": "pass|fail",
  "phase_match": "pass|fail",
  "backup_required": false,
  "backup_verified": false,
  "rollback_defined": false,
  "validation_defined": true,
  "required_fixes": [],
  "blocking_findings": [],
  "notes": "REQUIRED"
}
```

## Design

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
