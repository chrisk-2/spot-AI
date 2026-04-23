# SPOT FLEET STATE

## Current confirmed state

- Stage 1 / Milestone A is effectively locked from a runtime/policy standpoint
- Stage 2 operator shell is working
- Stage 3 read-only monitoring and alert awareness is working
- MCP transport is now working through the live wrapper endpoint
- Current remaining work is state/handoff cleanup, repo hygiene cleanup, and controlled operator-layer hardening

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

Do not change unless explicitly requested.

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

## MCP status

MCP wrapper is now operational enough to count as working transport, not theory.

### Confirmed MCP runtime behavior
Local checks against the wrapper on port `8001` show:

- `http://127.0.0.1:8001/spot` returns `307 Temporary Redirect` to `/spot/`
- `http://127.0.0.1:8001/spot/` returns `400 Bad Request: Missing session ID` on raw curl
- `http://127.0.0.1:8001/spot/mcp` returns `404 Not Found`
- `http://127.0.0.1:8001/spot/mcp/` returns `404 Not Found`

Meaning:

- the live mounted MCP streamable HTTP path is `/spot/`
- `/spot/mcp` is not the active route
- the `400 Missing session ID` result is expected for a raw non-session curl against a live MCP endpoint
- the path problem is resolved; future work should not waste time guessing alternate mount paths unless runtime changes again

### Practical conclusion
The MCP transport/path issue is no longer the blocker.

What is true now:

- wrapper is running
- endpoint shape is understood
- route mount is known
- session-based MCP behavior is what the server expects
- future effort should move to tool safety, control-surface consistency, and cleanup

## Checkpoint state

A checkpoint was saved and pushed after MCP confirmation.

### Latest saved checkpoint
- commit: `c252fd5`
- message: `checkpoint: 2026-04-23-02:52:27`

This is a real recoverable checkpoint, but not yet a clean long-term baseline because repo hygiene still needs cleanup.

## Cleanup completed

Recent cleanup completed before/around this phase:

- old archive tree removed
- old editor/save/bak clutter removed from live paths
- root-level duplicate `STATE.md` removed
- live tree reduced toward active runtime files plus intentional helper scripts
- monitoring state/history tree cleaned and stabilized
- MCP path confusion resolved by direct runtime testing instead of guessing

## Important reality

System is in a much better state now:

- filesystem is mostly sane
- monitoring is working
- alert-state tracking is working
- operator shell is coherent
- live state/history separation is clear
- MCP transport is working
- current baseline is stable enough to operate
- current baseline is not yet clean enough to call “finished” from a repo hygiene standpoint

## Open issues / next work

### 1. STATE/HANDOFF drift was real
This file had become stale and needed refresh.

Handoff rules remain useful, but STATE must stay current because it is the active runtime truth record for phase and next work.

### 2. Mutating API surface needs tightening
Current live app still exposes mutating routes outside the tokened `/admin/*` pattern:

- `/quarantine/{worker_name}`
- `/actions/restart-service/{worker_name}/{service_name}`

These need review and likely MCP-safe wrapping/alignment instead of leaving them as an inconsistent second control surface.

### 3. MCP tooling is now real, not hypothetical
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

### 4. Repo hygiene cleanup is required
Recent checkpoint commit included tracked virtualenv/runtime junk under `watch/.venv-mcp`.

This is not desired steady-state repo content.

What happened:

- `spot_save` produced a valid checkpoint
- the checkpoint also committed the MCP virtualenv and installed package tree
- repo is therefore recoverable but noisy and bloated

Needed next:

- add/verify ignore rules for local virtualenv and cache artifacts
- remove tracked venv artifacts from git index
- save a cleanup commit after verification

### 5. warmd exists but is not yet clearly wired into compose/runtime lifecycle
`warmd.py` exists in live code, but compose currently runs uvicorn only.

Need explicit decision:

- wire it in properly
- or leave it intentionally dormant and document that

### 6. compose secret handling is still rough
`SPOTCORE_ADMIN_API_TOKEN` is inline in compose.

Functional, but not the final security shape.

### 7. remediation backups still have local residue
`watch/backups/remediation-state` still exists locally.

Long term, backup artifacts should prefer shared storage.

### 8. helper-script sprawl still exists
The live tree is much cleaner, but there are still helper scripts under `watch/` that should eventually be grouped or documented more clearly.

## To-do list (current next phase)

### Immediate priority
- lock refreshed `STATE.md`
- confirm `HANDOFF.md` still matches real runtime paths and rules
- clean repo hygiene after accidental `.venv-mcp` commit
- save a clean follow-up checkpoint after cleanup
- continue MCP tool mapping against the current live routes
- do not redesign API first; wrap what already exists

### MCP work
- enumerate exact live endpoints to expose via MCP
- separate read actions from controlled mutating actions
- ensure MCP mutating actions only use safe spot-core entrypoints
- ensure MCP path does not bypass logging / verification / rollback
- decide whether quarantine/release/restart should be exposed via existing route names or normalized behind admin wrappers
- keep route assumptions tied to runtime behavior, not memory

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
- do not treat `HANDOFF.md` as state tracking
- do not treat the current checkpoint as clean repo hygiene until `.venv-mcp` is removed from tracking

