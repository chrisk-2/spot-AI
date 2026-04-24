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

This is no longer a theory stack. It is a live operational control surface.

## Latest confirmed operator milestone

Latest confirmed commit:

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

### Latest normal validation

`spot validate` passed:

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

### Latest smoke validation

`spot validate-smoke` passed:

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

### Current operator reality

The operator layer is now proven.

Confirmed good:

- local operator command exists
- human status works
- JSON status works
- quick health works
- validation works
- smoke validation works
- handoff capture works
- validator handles utility-worker transient slowness
- latest operator hardening commit is clean

This should be treated as a major milestone in Stage 2/operator usability.

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
- admin_restart_service: good
- admin_quarantine: good
- admin_release: good

### What was actually proven

#### admin_write_file

Confirmed by writing a harmless temp file on a worker and reading it back.

#### admin_write_local_file

Confirmed by writing a harmless temp file on spot-core and reading it back.

#### admin_restart_service

Initially failed due to worker sudo policy. After adding NOPASSWD sudo for `systemctl restart ollama`, it succeeded with real `returncode: 0` and active verification.

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

### Recent decisions

Working and populated.

### Latency stats

Working and populated.

This phase specifically fixed historical latency hydration so `avg_tok_per_sec` now backfills from historical data when possible.

### What was changed in `spotcore/app.py`

The following runtime/stat issues were fixed:

1. startup now hydrates:
   - warm models
   - routing audit
   - recent decisions
   - latency history
2. `seed_recent_decisions()` was added
3. `seed_latency_history()` was added and then improved
4. `build_decision_latency_index()` was added

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

Latest `spot validate` and `spot validate-smoke` confirmed all four ownership routes.

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

### 2. Restart verification is still weaker than ideal

`admin_restart_service` now truly works, but verification still mainly checks that the service is `active` afterward.

Better future hardening:

- compare timestamps or main PID before/after restart
- prove a restart actually occurred, not just that the service remained active

### 3. Mutating routes still exist outside the tokened admin namespace

Live `spotcore/app.py` still exposes mutating paths outside the cleaner `/admin/*` surface:

- `POST /quarantine/{worker_name}`
- `DELETE /quarantine/{worker_name}`
- `POST /actions/restart-service/{worker_name}/{service_name}`

They are functional, but the surface is inconsistent.

Future cleanup should normalize mutating control behind the admin pattern and/or MCP wrapper only.

### 4. Secrets handling is functional, not elegant

`SPOTCORE_ADMIN_API_TOKEN` handling is working, but secret placement and compose hygiene are still not the final security shape.

### 5. Repo/runtime hygiene is improved but not fully curated

The active tree is much cleaner than before, but helper-script sprawl under `watch/` still exists and documentation/grouping can be improved.

### 6. warmd wiring is still unresolved

`warmd.py` exists, but there is still no clearly documented final decision about whether it should be wired into runtime lifecycle or intentionally remain dormant.

### 7. Operator UI polish is basic

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

### What it is not yet

It is not yet a fully polished production platform with perfect surface hygiene, connector-mode ergonomics, final secret handling, and final operator UI.

## Current next objective

### Primary next objective

Harden and clean the control surface now that functionality is proven.

This means:

1. normalize mutating APIs
2. tighten verification semantics for restarts
3. clean up repo/runtime hygiene and document live files versus leftovers
4. decide whether to split read-only MCP and admin MCP into separate wrappers/connectors
5. decide whether `warmd.py` should be wired into runtime lifecycle or explicitly marked dormant

### Why this is next

Because the system now works.

The next phase should not be “make it basically function.”
The next phase should be “make the live operational surface cleaner, safer, and easier to maintain.”

## Suggested next tasks in order

### 1. Control-surface cleanup

- review all mutating routes in `spotcore/app.py`
- decide which should remain directly exposed
- move toward a single coherent admin/control surface

### 2. Restart verification hardening

- update restart verification to compare timestamp/PID before and after
- eliminate false-positive style checks permanently

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

### 4. Repo hygiene / live-file map

- identify live files vs legacy leftovers
- document the watch scripts that are actually in use
- document what can be archived or removed

### 5. Secret handling cleanup

- move tokens/env handling to a cleaner pattern
- reduce inline secret exposure in runtime config

### 6. warmd lifecycle decision

- read current `warmd.py`
- inspect current runtime wiring
- decide whether it should be active, dormant, or archived
- do not wire it blindly

## Do not do next

- do not redesign scheduler routing right now
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
- quarantine
- release
- local spot command
- human-readable spot status
- machine-readable spot status-json
- spot quick-health
- spot validate
- spot validate-smoke
- spot_save

### Confirmed still rough

- restart verification quality
- API surface consistency
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
- expose those actions through MCP
- expose a local operator cockpit
- validate routing and admin behavior
- smoke-test quarantine/release behavior without restart

The next phase is not rescue. It is hardening and cleanup.
