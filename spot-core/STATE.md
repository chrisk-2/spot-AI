# SPOT FLEET STATE

## Current confirmed state

- Stage 1 / Milestone A is effectively locked
- Stage 2 operator shell is working
- Stage 3 read-only monitoring and alert awareness is working

## Current live repo/runtime

- repo root: `/home/ogre/spot-stack`
- core app: `/home/ogre/spot-stack/spot-core/spotcore/app.py`
- cluster config: `/home/ogre/spot-stack/spot-core/config/cluster_config.json`
- compose file: `/home/ogre/spot-stack/docker-compose.yml`
- state file: `/home/ogre/spot-stack/spot-core/STATE.md`
- handoff file: `/home/ogre/spot-stack/HANDOFF.md`

## Current operator shell status

`spot-ops.sh` is the primary operator entrypoint.

Current operator commands confirmed working in this phase include:

- status
- validate
- validate-smoke
- health
- routing
- audit
- net-basics
- endpoints
- dns-check
- reverse-proxy-check
- quarantine-state
- remediation
- quarantine
- release
- logs
- quick-health
- dns-latency
- net-latency
- monitor-latest
- monitor-history
- monitor-alerts
- alert-state
- alert-history

## Monitoring / alerting state

The read-only monitoring stack is now in place and working:

- fleet snapshot writer exists and runs by timer
- monitor summary history is being written
- latest alert state is being written
- alert transitions are being written as JSONL
- alert-state and alert-history are readable through `spot-ops.sh`

Current monitor files:

- `/home/ogre/spot-stack/watch/state/history/monitor-summary.jsonl`
- `/home/ogre/spot-stack/watch/state/history/monitor-alert-latest.json`
- `/home/ogre/spot-stack/watch/state/history/monitor-alert-transitions.jsonl`
- `/home/ogre/spot-stack/watch/state/history/snapshots/`

## Current fleet ownership lock

- general -> spot-worker-01
- utility -> spot-worker-02
- coding -> spot-worker-03
- heavy -> spot-worker-04

## Current config/runtime notes

### cluster_config.json
Confirmed live config includes:

- role priority:
  - heavy: worker-04, worker-03, worker-01
  - coding: worker-03
  - general: worker-01
  - utility: worker-02
  - watcher: worker-02
- warm model policy enabled
- watcher role mapped to worker-02
- backup/log roots in app.py point to shared storage paths under `/mnt/collective/...`

### docker-compose.yml
Confirmed live compose:

- mounts `./spot-core` and `./watch`
- mounts `/mnt/collective`
- mounts shared memory path from `/mnt/collective/fleet/spot-core/shared_memory`
- injects `SPOTCORE_ADMIN_API_TOKEN` via inline env
- runs uvicorn for `spotcore.app:app`

## Current API reality

Confirmed from live `app.py`:

### tokened admin routes
- `POST /admin/validate`
- `POST /admin/restart-service`
- `POST /admin/read-file`
- `POST /admin/write-file`

### other mutating/runtime routes currently present
- `POST /quarantine/{worker_name}`
- `DELETE /quarantine/{worker_name}`
- `POST /actions/restart-service/{worker_name}/{service_name}`

### read-only/runtime routes currently present
- `GET /health`
- `GET /routing`
- `GET /fleet/ping`
- `GET /stats/latency`
- `GET /stats/recent-decisions`
- `GET /stats/routing-audit`
- `POST /exec`

## Cleanup completed

Recent cleanup completed:

- old archive tree removed
- old editor/save/bak clutter removed from live paths
- root-level duplicate `STATE.md` removed
- live tree now reduced to active runtime files plus intentional helper scripts
- monitoring state/history tree cleaned and stabilized

## Important reality

System is in a much better state now:

- filesystem is sane
- monitoring is working
- alert-state tracking is working
- operator shell is coherent
- live state/history separation is clear
- current baseline is stable enough to checkpoint

## Open issues / next work

### 1. STATE/HANDOFF drift was real
This file had become stale and needed refresh.
HANDOFF also still referenced a nonexistent compose path before correction.

### 2. Mutating API surface needs tightening
Current live app exposes mutating routes outside the tokened `/admin/*` pattern:

- `/quarantine/{worker_name}`
- `/actions/restart-service/{worker_name}/{service_name}`

These need review and likely MCP-safe wrapping/alignment instead of leaving them as an inconsistent second control surface.

### 3. MCP tooling is the next major step
This is now the right next evolution, using the system as it already exists instead of redesigning it.

What MCP changes in practical terms:

- without MCP: ChatGPT can only tell the operator what to do
- with MCP: ChatGPT can operate Spot through spot-core inside policy

What it does in real terms:

#### Read
- get fleet health
- inspect routing
- check quarantine state
- pull audit logs

#### Controlled actions
- restart a service
- quarantine a worker
- release a worker

And all of that must still flow through:

- risk classification
- backup-first when needed
- verification
- logging
- rollback paths

Clean definition:

> The MCP tool is the interface that allows ChatGPT to operate Spot safely through spot-core without bypassing policy, logging, or control.

### 4. warmd exists but is not yet clearly wired into compose/runtime lifecycle
`warmd.py` exists in live code, but compose currently runs uvicorn only.
Need explicit decision:
- wire it in properly
- or leave it intentionally dormant and document that

### 5. compose secret handling is still rough
`SPOTCORE_ADMIN_API_TOKEN` is inline in compose.
Functional, but not the final security shape.

### 6. remediation backups still have local residue
`watch/backups/remediation-state` still exists locally.
Long term, backup artifacts should prefer shared storage.

### 7. helper-script sprawl still exists
The live tree is much cleaner, but there are still helper scripts under `watch/` that should eventually be grouped or documented more clearly.

## To-do list (next phase)

### Priority next
- update and lock STATE.md and HANDOFF.md
- save checkpoint after validation
- define exact MCP tool mapping to current live routes
- do not redesign API first; wrap what already exists

### MCP work
- enumerate exact live endpoints to expose via MCP
- separate read actions from controlled mutating actions
- ensure MCP mutating actions only use safe spot-core entrypoints
- ensure MCP path does not bypass logging / verification / rollback
- decide whether quarantine/release/restart should be exposed through existing route names or normalized behind admin wrappers

### API hardening
- review auth coverage on all mutating routes
- remove inconsistent “second path” behavior where mutating routes exist outside the intended admin control pattern
- keep request/response behavior stable unless explicitly changing it

### Monitoring follow-up
- optional: surface alert state to dashboard/webhook/Discord
- optional: add cleanup/retention policy for snapshot history
- optional: review whether DNS auto-fix behavior in fleet-watch should remain there or be separated more cleanly from read-only monitoring expectations

### Runtime/ops follow-up
- decide whether to wire warmd into compose
- move/normalize remaining backup artifacts to shared storage where appropriate
- optionally group one-off watch helper scripts into a tools area later, without changing behavior now

## Do not do next

- do not redesign scheduler routing
- do not change role ownership
- do not expand scope into UI work yet
- do not weaken backup/logging/verification enforcement
- do not invent new API names before reading runtime
- do not treat HANDOFF.md as state tracking
