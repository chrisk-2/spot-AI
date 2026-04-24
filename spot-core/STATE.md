# SPOT FLEET STATE

## Current confirmed state

Spot is now in a materially better state than at the start of this phase.

What is now confirmed working end-to-end:

- spot-core control plane is live and responding
- live MCP wrapper is working through the connected ChatGPT MCP path
- local file read/write on spot-core works through MCP
- remote worker file read/write works through MCP
- remote service restart works through MCP
- quarantine and release work through MCP
- routing audit stats are populated
- recent decision stats are populated
- latency stats are populated, including historical avg_tok_per_sec backfill
- Cloudflare tunnel for MCP is running persistently under systemd user services
- wrapper service is running persistently under systemd user services
- local `spot` operator command is promoted and working
- `spot status` is now human-readable
- `spot status-json` preserves machine-readable status output
- `spot quick-health` is working
- `spot validate` is working
- `spot validate-smoke` is working
- `spot_save` captures runtime handoff data and quick status correctly
- restart-service verification now proves real process/lifecycle transition
- legacy mutating routes are marked deprecated and point to `/admin/*`
- owned roles now prefer the owner when the owner is healthy and admissible
- worker config backup script is implemented and source-controlled
- worker config backups successfully executed and verified on all four AI workers
- worker config backups are scheduled via cron every 6 hours on all four AI workers
- worker backup root is `/mnt/collective/backups/<worker>/worker-config/<timestamp>`
- worker backup `latest` symlink is maintained per worker
- worker-03 GitHub SSH access is working and `/home/ogre/spot-stack` is current
- worker-02 GPU runtime behavior is documented and inventoried

This is no longer a theory stack. It is a live operational control surface.

## Current worker, Codex, and backup status

### Worker-02 GPU status

`spot-worker-02` remains the owned `utility` worker. Do not change routing ownership unless explicitly requested.

Hardware:

- GPU0: Quadro M4000 8 GB
- GPU1: GTX 1060 6 GB

Current confirmed runtime:

- live Ollama override: `/etc/systemd/system/ollama.service.d/gpu.conf`
- override content: `CUDA_VISIBLE_DEVICES=0`
- utility model: `phi3.5:latest`
- observed warm runtime loaded `phi3.5:latest` on the GTX 1060 while the Quadro was idle
- `spot validate` passed clean after confirming the override

Known caveat:

- worker-02 can still be slow or overly verbose, especially on cold starts
- this is treated as model/runtime behavior, not a routing failure

Repo evidence:

- worker-02 runtime snapshot is stored under `fleet-inventory/workers/spot-worker-02/`

### Worker-03 Codex and Git status

Worker-03 is now usable as the Codex/code workstation.

Confirmed:

- Codex CLI updated to `v0.124.0`
- `codex_spot.sh` launcher works
- `~/.starfleet-stage` is a local Git repo
- Codex created and committed `fleet-docs/WORKSPACE_MAP.md`
- Codex created and committed `fleet-docs/PORTING_NOTES.md`
- GitHub SSH authentication works
- `/home/ogre/spot-stack` exists on worker-03 and tracks `git@github.com:chrisk-2/spot-AI.git`
- worker-03 pulled latest through `483173a`

Important distinction:

- worker-03 has Codex CLI/tooling installed
- worker-03 does not have a Codex Ollama model
- Codex is for repo/workspace editing, not `/exec` model routing

### Worker backup status

Worker config backups are now operational for the four AI workers.

Covered workers:

- `spot-worker-01`
- `spot-worker-02`
- `spot-worker-03`
- `spot-worker-04`

Backup implementation:

- source-controlled script: `scripts/spot-worker-backup.sh`
- deployed script path on workers: `/home/ogre/spot-worker-backup.sh`
- schedule: cron every 6 hours
- cron entry: `17 */6 * * * /home/ogre/spot-worker-backup.sh >/home/ogre/spot-worker-backup.log 2>&1`
- target root: `/mnt/collective/backups`
- per-worker path: `/mnt/collective/backups/<worker>/worker-config/<timestamp>`
- latest pointer: `/mnt/collective/backups/<worker>/worker-config/latest`

Manual verification completed:

- `spot-worker-01` backup complete
- `spot-worker-02` backup complete
- `spot-worker-03` backup complete
- `spot-worker-04` backup complete

Backup scope:

- hostname and OS metadata
- mount and disk state
- systemd timer list
- crontab for `ogre`
- Ollama service definition and environment
- NVIDIA GPU inventory
- Ollama model list
- package list
- selected `/home/ogre` operational scripts and staged docs
- metadata and SHA256 manifest

Intentional exclusions:

- Ollama model blobs are not backed up
- large model data remains a policy decision, likely re-pull instead of backup

Known storage reality:

- `/mnt/collective/backups` is the current reliable common target
- `/mnt/unimatrix6` exists on some nodes but is not uniformly verified across the fleet
- `spot-ui-01` / `192.168.10.12` was discovered but intentionally deferred until UI architecture is decided

Remaining backup work:

- add backup freshness visibility to `spot status` or `spot_save`
- decide long-term Unimatrix6 vs `/mnt/collective` strategy
- decide model blob backup policy


## Latest confirmed hardening milestone

Latest uncommitted verified work in `spotcore/app.py`:

- restart verification hardening
- legacy mutating route deprecation markers
- ownership-first routing fix

Validation after patch:

```text
RESULT: PASS (15 checks, 0 warnings)
```

Confirmed ownership routes after the fix:

- `general -> spot-worker-01`
- `coding -> spot-worker-03`
- `heavy -> spot-worker-04`
- `utility -> spot-worker-02`

### Restart verification hardening

`admin_restart_service` and the legacy `/actions/restart-service/{worker_name}/{service_name}` route no longer merely check that a service is `active` after restart.

Current verification captures `systemctl show` metadata before and after restart and requires both:

1. restart command return code is `0`
2. service is active after restart
3. at least one lifecycle/process field changed

Compared fields:

- `MainPID`
- `ExecMainPID`
- `ActiveEnterTimestampMonotonic`
- `InactiveEnterTimestampMonotonic`
- `NRestarts`

Live proof from `spot-worker-01` / `ollama` restart:

```text
active_after: true
restart_observed: true
changed_fields:
  - MainPID
  - ExecMainPID
  - ActiveEnterTimestampMonotonic
  - InactiveEnterTimestampMonotonic
restart_returncode: 0
```

This closes the earlier false-positive restart weakness.

### Legacy mutating route deprecation markers

The legacy mutating routes remain present for compatibility, but now identify themselves as deprecated and point callers to the preferred admin route.

Legacy routes:

- `POST /quarantine/{worker_name}`
- `DELETE /quarantine/{worker_name}`
- `POST /actions/restart-service/{worker_name}/{service_name}`

Current returned metadata:

```json
{
  "deprecated_route": true,
  "preferred_route": "/admin/..."
}
```

Preferred replacements:

- `/admin/quarantine`
- `/admin/release`
- `/admin/restart-service`

The routes were not removed. Payload compatibility is preserved.

### Ownership-first routing fix

A real routing bug was found after restart hardening.

Observed failure:

```text
heavy -> spot-worker-01
expected -> spot-worker-04
```

Audit classified this as:

```text
route_class: violation
violation_reason: selected_non_owner_while_owner_admissible
owner_worker: spot-worker-04
selected_worker: spot-worker-01
```

Root cause:

- `gather_candidates()` collected all role-priority workers
- scoring could rank a non-owner above the role owner
- `spot-worker-01` could beat `spot-worker-04` for heavy because it had favorable score inputs and `qwen2.5:14b` installed

Fix:

- for owned roles, if the owner is healthy and admissible, candidate gathering is restricted to the owner
- fallback candidates remain available when the owner is not healthy or not admissible
- explicit manual worker override still works through `req.worker`

This preserves fallback behavior while enforcing the locked ownership model.

### Latest validation after ownership fix

After patch and `docker compose restart spot-core`, validation passed:

```text
RESULT: PASS (15 checks, 0 warnings)
```

Confirmed:

- `general -> spot-worker-01`
- `coding -> spot-worker-03`
- `heavy -> spot-worker-04`
- `utility -> spot-worker-02`
- audit append occurred
- JSONL audit entries valid
- fleet status valid
- routing audit summary valid
- no quarantined hosts
- `/admin/validate` works
- `/admin/read-file` works

## Previous confirmed operator milestone

Latest confirmed commit before this hardening work:

```text
18d7916 feat: improve operator status and validator retries
```

Changed files:

- `/home/ogre/spot-stack/watch/spot-ops.sh`
- `/home/ogre/spot-stack/watch/fleet-validate.sh`
- `/home/ogre/spot-stack/watch/spot-save.sh`

The git tree was confirmed clean before smoke validation.

### Operator command promotion

The local `spot` command is now the primary operator entry point.

Confirmed working commands:

- `spot status`
- `spot status-json`
- `spot quick-health`
- `spot validate`
- `spot validate-smoke`
- `spot_save`

Raw endpoints remain valid for debugging, but normal operator flow should now go through `spot`.

### Human-readable status

`spot status` now provides a cockpit view instead of raw JSON.

Expected shape:

```text
=== SPOT STATUS ===
Core:        OK (uptime: <seconds>s)
Routing:     OK (<n> primary, <n> fallback, <n> violations)

Workers:
  spot-worker-01  [general]  OK
  spot-worker-02  [utility]  OK
  spot-worker-03  [coding]   OK
  spot-worker-04  [heavy]    OK

Fleet:       ALL SYSTEMS NOMINAL
```

The old raw JSON behavior is preserved as:

```bash
spot status-json
```

Validated with:

```bash
spot status-json | jq .
```

### Quick health status

`spot quick-health` is confirmed working.

It checks:

- spot-core `/health`
- `/fleet/ping`
- `/stats/routing-audit`
- endpoint reachability

Current endpoint set includes:

- `spot-core-health`
- `opnsense-https`
- `dns-core-http`
- `starfleet-core-https`
- `spot-ollama`

Latest confirmed endpoint result:

```text
ok_count=5
fail_count=0
```

### Validator retry hardening

`/home/ogre/spot-stack/watch/fleet-validate.sh` was hardened after observing transient utility validation failures.

Observed failure modes:

- utility route request timed out during `/exec`
- utility route returned transient HTTP 503

Classification:

- not dead worker
- not bad routing
- not ownership failure
- consistent with `spot-worker-02` being slow or briefly busy

`utility` uses `phi3.5:latest`.

Current behavior:

- retry once if `http_json POST /exec` fails to execute
- retry once if HTTP response is:
  - `429`
  - `503`
  - `504`
- persistent failure still fails validation
- real non-2xx after retry still fails validation

This prevents false red-alert behavior while preserving failure signal.

### Latest smoke validation

`spot validate-smoke` passed before this hardening round:

```text
RESULT: PASS (21 checks, 0 warnings)
```

Smoke target:

```text
spot-worker-01
```

Confirmed quarantine lifecycle:

```text
POST /quarantine/spot-worker-01
fleet/ping -> quarantined=true eligible=false
fleet-status -> quarantined=true

DELETE /quarantine/spot-worker-01
fleet/ping -> quarantined=false eligible=true
fleet-status -> quarantined=false
```

This proves quarantine/release works through the operator validation path without restart.

### spot_save quick status fix

`/home/ogre/spot-stack/watch/spot-save.sh` now includes quick runtime status.

Bug fixed:

```text
spot-core: null
```

Cause:

- script queried `.status`
- `/health` returns `.ok` and `.uptime_sec`

Correct current output:

```text
spot-core: OK uptime_sec=<seconds>
```

`spot_save` now captures:

- git status
- staged diff summary
- staged files
- current commit
- `HANDOFF.md`
- `STATE.md`
- `app.py`
- cluster config
- compose
- MCP wrapper
- MCP app
- systemd services
- runtime health
- latency snapshot
- recent decisions
- short systemd status
- docker status
- new-chat block

## Current live repo/runtime

- repo root: `/home/ogre/spot-stack`
- core app: `/home/ogre/spot-stack/spot-core/spotcore/app.py`
- cluster config: `/home/ogre/spot-stack/spot-core/config/cluster_config.json`
- compose file: `/home/ogre/spot-stack/docker-compose.yml`
- state file: `/home/ogre/spot-stack/spot-core/STATE.md`
- handoff file: `/home/ogre/spot-stack/HANDOFF.md`
- MCP wrapper repo: `/home/ogre/spot-mcp`
- MCP wrapper main file: `/home/ogre/spot-mcp/spot_mcp_wrapper.py`
- MCP wrapper app: `/home/ogre/spot-mcp/app.py`
- MCP env file: `/home/ogre/spot-mcp/spot-mcp.env`

## Current MCP / connector state

### Wrapper/runtime

Confirmed live working shape:

- wrapper process runs via user systemd as `spot-mcp.service`
- cloudflared tunnel runs via user systemd as `mcp-tunnel.service`
- wrapper is served locally on `127.0.0.1:8001`
- tunnel exposes the MCP endpoint through `mcp.starfleetcore.com`
- ChatGPT connector is using the live wrapper and current tool schema

### Confirmed exposed MCP tools

Read / status:

- `health`
- `routing`
- `fleet_ping`
- `stats_latency`
- `stats_recent_decisions`
- `stats_routing_audit`
- `admin_read_file`
- `admin_read_local_file`

Mutating / controlled actions:

- `admin_write_file`
- `admin_write_local_file`
- `admin_validate`
- `admin_restart_service`
- `admin_quarantine`
- `admin_release`

### Practical conclusion

The MCP layer is no longer the blocker.

The main MCP issues that were fixed in this phase were:

- wrapper schema drift
- duplicate tool definitions in `spot_mcp_wrapper.py`
- missing local-file tools in wrapper schema
- stale connector schema until reconnect/recreate
- worker restart blocked by sudo password prompt

All of those are now resolved.

## Current operator/control status

### Confirmed MCP actions tested successfully

#### Read / inspect

- health: good
- routing: good
- fleet_ping: good
- stats_routing_audit: good
- stats_recent_decisions: good
- stats_latency: good
- admin_read_file: good
- admin_read_local_file: good

#### Write / mutate

- admin_write_file: good
- admin_write_local_file: good
- admin_restart_service: good, now with transition verification
- admin_quarantine: good
- admin_release: good

### What was actually proven

#### admin_write_file

Confirmed by writing a harmless temp file on a worker and reading it back.

#### admin_write_local_file

Confirmed by writing a harmless temp file on spot-core and reading it back.

#### admin_restart_service

Initially failed due to worker sudo policy. After adding NOPASSWD sudo for `systemctl restart ollama`, it succeeded with real `returncode: 0`.

It has now been hardened again so verification proves a real process/lifecycle transition, not just `active` state.

#### admin_quarantine / admin_release

Confirmed with live test on `spot-worker-03`.

Quarantine test result:

- watch state flipped to quarantined = true
- eligible = false
- remediation state marked quarantined = true
- backup artifacts were created before mutation

Release test result:

- watch state flipped back to quarantined = false
- eligible = true
- remediation state cleared
- penalty removed
- backup artifacts were created before mutation

Latest operator smoke validation also confirmed quarantine/release on `spot-worker-01` through `spot validate-smoke`.

## Current stats/runtime state

### Routing audit

Working and populated.

Latest validation confirmed routing audit append behavior.

Note: historical routing violations may remain visible in the recent audit window until displaced by newer clean entries. Treat `spot validate` and current audit entries as the immediate truth after routing fixes.

### Recent decisions

Working and populated.

### Latency stats

Working and populated.

This phase specifically fixed historical latency hydration so `avg_tok_per_sec` now backfills from historical data when possible.

### What was changed in `spotcore/app.py`

The following runtime/stat issues were fixed earlier:

1. startup now hydrates:
   - warm models
   - routing audit
   - recent decisions
   - latency history
2. `seed_recent_decisions()` was added
3. `seed_latency_history()` was added and then improved
4. `build_decision_latency_index()` was added

The following hardening changes are now also active in `spotcore/app.py`:

1. `systemctl_show_service()` added
2. `service_restart_verified()` added
3. admin restart path uses before/after systemd metadata
4. legacy restart path uses before/after systemd metadata
5. legacy mutating routes return deprecation metadata
6. `gather_candidates()` enforces ownership-first candidate restriction when the owner is healthy and admissible

### Current latency backfill behavior

Historical `avg_tok_per_sec` now seeds using this order:

1. exact `eval_duration` when present
2. matching decision-history latency value when present
3. estimated `eval_count / total_duration` as fallback

This is now confirmed live after restart.

### Verified live latency output

After restart, `/stats/latency` returned non-null `avg_tok_per_sec` values for all workers.

That confirms the patch is active and functioning.

### Current latency note

`spot-worker-02` is healthy but slow. It is the expected source of transient utility route delay/backpressure.

Do not treat utility validation flake as a routing failure unless health, quarantine, audit, or repeated retry failure proves it.

## Current fleet ownership lock

- general -> spot-worker-01
- utility -> spot-worker-02
- coding -> spot-worker-03
- heavy -> spot-worker-04

Do not change unless explicitly requested.

Latest `spot validate` confirmed all four ownership routes after the ownership-first routing fix.

## Current config/runtime notes

### cluster_config.json

Still treated as live authority for routing and policy.

### docker-compose.yml

Confirmed live compose is still the active runtime entry for spot-core.

### spot-core app runtime

`spotcore/app.py` is the actual control-plane source of truth and has been actively modified in this phase.

### wrapper runtime

`/home/ogre/spot-mcp/app.py` correctly imports:

```python
from spot_mcp_wrapper import mcp
```

and mounts the streamable HTTP app.

That wiring is confirmed correct.

## Systemd / persistence state

### Confirmed user services

- `spot-mcp.service`
- `mcp-tunnel.service`

### Confirmed goals achieved

- runs in background
- survives shell close
- survives reboot via lingering/user systemd setup

This was a major goal and is now complete.

## Important things that were wrong and are now fixed

### 1. Bad systemd unit for spot-mcp

There were duplicate `ExecStart=` lines in `spot-mcp.service`. Fixed.

### 2. Wrong assumption about wrapper venv path

Earlier service definitions pointed at a nonexistent venv path under `watch/.venv`. Fixed by using the real wrapper venv under `/home/ogre/spot-mcp/.venv`.

### 3. Wrapper schema missing local file tools

Added:

- `admin_read_local_file`
- `admin_write_local_file`

### 4. Duplicate tool definitions in wrapper

Duplicate `admin_write_file` / `admin_validate` definitions caused warnings and schema confusion. Removed.

### 5. Connector schema staleness

Required reconnect/recreate before ChatGPT saw the updated tool set. Resolved.

### 6. stats_recent_decisions empty

Fixed by hydrating from persisted decision history on startup.

### 7. stats_latency empty / avg_tok_per_sec null

Fixed by hydrating from exec history and later improving the seeder to backfill tok/sec from decision history and fallback estimation.

### 8. admin_restart_service false-positive behavior

The first restart test looked successful only because verification checked `active` even though the `sudo systemctl restart` command itself failed.

The underlying worker sudo policy was then fixed, and restart now truly works.

This has now been hardened further: restart verification checks before/after systemd process/lifecycle metadata and requires observed transition.

### 9. Hidden operator interface

`watch/spot-ops.sh` existed but was not promoted as the obvious local operator entry point.

Now `spot` is the primary local operator command.

### 10. spot quick-health jq expression bug

`spot quick-health` had a jq object merge issue.

Fixed by wrapping the merge expression:

```jq
endpoints: ($endpoints.summary + {items: $endpoints.items})
```

### 11. Validator false failures from utility latency/backpressure

`fleet-validate.sh` now retries once on:

- route request execution failure
- transient HTTP 429
- transient HTTP 503
- transient HTTP 504

### 12. Raw-only operator status

`spot status` is now human-readable.

Raw JSON is preserved as:

```bash
spot status-json
```

### 13. spot_save quick status bug

`spot_save` previously showed:

```text
spot-core: null
```

because it queried `.status`.

Fixed to use `.ok` and `.uptime_sec` from `/health`.

### 14. Legacy mutating routes were unclear

Legacy mutating routes still existed outside `/admin/*`:

- `POST /quarantine/{worker_name}`
- `DELETE /quarantine/{worker_name}`
- `POST /actions/restart-service/{worker_name}/{service_name}`

They are now explicitly marked as deprecated in responses and point to the preferred `/admin/*` route.

### 15. Scheduler scoring could beat ownership

`gather_candidates()` previously gathered all role-priority candidates and then scoring could select a non-owner even while the owner was healthy and admissible.

Observed real violation:

```text
heavy -> spot-worker-01
expected -> spot-worker-04
```

Fixed by restricting candidates to the role owner when the owner is healthy and admissible.

## Things still wrong, rough, or not final

These are the real remaining issues, not imaginary ones.

### 1. Developer Mode dependency in ChatGPT

Custom MCP use is still tied to ChatGPT Developer Mode for this workflow.

That means:

- memory behavior is worse in that mode
- this is a platform limitation, not a Spot server bug

Current workaround:

- keep a normal-memory chat for planning/history
- keep a dev-mode chat for live MCP actions

### 2. Full control-surface cleanup is not complete

Legacy mutating routes are now marked deprecated, but they still exist for compatibility.

Future cleanup should eventually decide whether to keep them as compatibility wrappers, gate them harder, or remove them after confirming no scripts depend on them.

### 3. Secrets handling is functional, not elegant

`SPOTCORE_ADMIN_API_TOKEN` handling is working, but secret placement and compose hygiene are still not the final security shape.

`spot_save` can expose compose/env material in captured output, so secret hygiene should be handled before wider sharing.

### 4. Repo/runtime hygiene is improved but not fully curated

The active tree is much cleaner than before, but helper-script sprawl under `watch/` still exists and documentation/grouping can be improved.

### 5. warmd wiring is still unresolved

`warmd.py` exists, but there is still no clearly documented final decision about whether it should be wired into runtime lifecycle or intentionally remain dormant.

### 6. Operator UI polish is basic

`spot status` is functional but still basic.

It is good enough for operations, but not a final dashboard.

## Current project reality

### What this system is now

This is now a real distributed control plane with:

- routing
- health
- monitoring state
- audit state
- policy-aware control actions
- backup/verification on state changes
- live MCP control from ChatGPT
- local operator command surface
- validation workflow
- smoke validation workflow
- handoff capture workflow
- transition-proven service restart verification
- compatibility-marked legacy mutating routes
- ownership-first routing enforcement

### What it is not yet

It is not yet a fully polished production platform with perfect surface hygiene, connector-mode ergonomics, final secret handling, and final operator UI.

## Current next objective

### Primary next objective

Finish the backup visibility and Stage 2 cleanup path now that core behavior, worker-02 GPU state, worker-03 Codex/Git, and worker config backups are proven.

This means:

1. add backup freshness visibility to `spot status` or `spot_save`
2. run `spot validate-smoke` after the latest hardening changes
3. commit/checkpoint the current repo state if smoke passes
4. clean up repo/runtime hygiene and document live files versus leftovers
5. decide whether to split read-only MCP and admin MCP into separate wrappers/connectors
6. decide whether `warmd.py` should be wired into runtime lifecycle or explicitly marked dormant

### Why this is next

Because the system now works and the latest high-risk logic bugs were fixed.

The next phase should not be “make it basically function.”
The next phase should be “make the live operational surface cleaner, safer, and easier to maintain.”

## Suggested next tasks in order

### 1. Final validation and checkpoint

- run `spot validate-smoke`
- run `spot validate`
- run `spot_save`
- confirm commit/push

### 2. Repo hygiene / live-file map

- identify live files vs legacy leftovers
- document the watch scripts that are actually in use
- document what can be archived or removed

### 3. Split MCP by privilege

Recommended future structure:

#### Spot ReadOnly MCP

- health
- routing
- fleet_ping
- stats_latency
- stats_recent_decisions
- stats_routing_audit
- read-local-file
- read-file

#### Spot Admin MCP

- write-local-file
- write-file
- restart-service
- quarantine
- release
- validate

This would make normal operational use safer and more production-like.

### 4. Secret handling cleanup

- move tokens/env handling to a cleaner pattern
- reduce inline secret exposure in runtime config
- prevent `spot_save` output from casually exposing secrets

### 5. warmd lifecycle decision

- read current `warmd.py`
- inspect current runtime wiring
- decide whether it should be active, dormant, or archived
- do not wire it blindly

## Do not do next

- do not redesign scheduler routing beyond the ownership-first fix unless a new verified bug appears
- do not change role ownership
- do not rip out the current MCP stack just because Developer Mode is annoying
- do not weaken backup/verification behavior
- do not assume helper scripts are dead without checking runtime use first
- do not conflate ChatGPT platform limits with Spot server bugs
- do not casually change request/response formats
- do not introduce new auth patterns without explicit security design

## Validation commands for next session

Start with:

```bash
cd /home/ogre/spot-stack
git status --short
spot status
spot quick-health
spot validate
```

Full operator lifecycle check:

```bash
spot validate-smoke
```

Machine-readable operator status:

```bash
spot status-json | jq .
```

Handoff capture:

```bash
spot_save
```

## Short status summary

### Confirmed good

- spot-core runtime
- wrapper runtime
- tunnel runtime
- MCP connection
- local file read/write
- worker file read/write
- stats hydration
- latency backfill
- service restart
- restart transition verification
- quarantine
- release
- local spot command
- human-readable spot status
- machine-readable spot status-json
- spot quick-health
- spot validate
- spot validate-smoke from prior milestone
- spot_save
- ownership-first routing
- legacy mutating route deprecation metadata
- worker-02 GPU override documented and inventoried
- worker-03 Git/Codex workflow
- worker config backups manually verified on all four AI workers
- worker config backups scheduled every 6 hours
- worker backup script source-controlled

### Confirmed still rough

- final smoke validation after latest hardening still needs to be run
- full API surface cleanup is not complete
- secret/config hygiene
- helper-script/live-file clarity
- Developer Mode dependency for custom MCP usage in ChatGPT
- warmd lifecycle decision
- final operator UI polish

## Plain-English bottom line

Spot is now operationally real.

The biggest unknowns from earlier in the project are gone. The stack can now:

- inspect itself
- change itself
- back itself up before state changes
- verify those changes
- prove service restarts by actual lifecycle/process transition
- expose those actions through MCP
- expose a local operator cockpit
- validate routing and admin behavior
- smoke-test quarantine/release behavior without restart
- enforce role ownership before score-based routing wins

The next phase is not rescue. It is hardening and cleanup.
