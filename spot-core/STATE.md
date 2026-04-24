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
- admin token was removed from tracked `docker-compose.yml` and is now loaded from ignored `spot-core/.env`
- `spot_save` now shows worker backup status in handoff output
- `spot validate` now checks worker backup freshness
- worker backup freshness threshold defaults to 8 hours via `SPOT_BACKUP_MAX_AGE_HOURS`
- routing audit write failures are explicitly logged with path, timestamp, role, status, worker, and exception detail
- validator secret-regression scan is implemented and confirmed clean
- legacy per-GPU worker services on worker-02 and worker-03 are disabled after backup and validation
- worker home cleanup/archive pass completed on worker-01, worker-02, and worker-03
- worker-04 inspected and left alone because it was already clean
- final fleet sanity scan shows only `ollama.service` active on workers and only port `11434` listening for runtime traffic
- worker-02 Ollama is now pinned by UUID to physical GPU 0 / Quadro M4000 8GB
- worker-02 physical GPU 1 / GTX 1060 6GB is free for monitoring/watch/camera workloads
- utility role is now included in warm-model policy
- worker-02 `phi3.5:latest` is now an explicit warm target
- latest normal validation passed with 20 checks and 0 warnings
- latest smoke validation passed with 26 checks and 0 warnings

Latest validation after worker-02 GPU pin and warm-policy tuning:

```text
spot validate:       RESULT: PASS (20 checks, 0 warnings)
spot validate-smoke: RESULT: PASS (26 checks, 0 warnings)
```

Latest checkpoint commit before this tuning phase:

```text
c93c870 state: record worker cleanup progress
```

This is no longer a theory stack. It is a live operational control surface.

## Current worker, Codex, and backup status

### Worker cleanup audit status

A cleanup inventory and archive pass was run across all four workers after the hostname/role migration.

Final runtime shape:

```text
spot-core -> workers -> ollama:11434
```

Confirmed from final fleet sanity scan:

- all four workers expose only Ollama on port `11434` for runtime traffic
- all four workers show only `ollama.service` as the active cleanup-relevant runtime service
- no worker shows active legacy `878x`, `879x`, `5050`, uvicorn, gunicorn, or sidecar Python APIs
- current Spot routing still sees all four workers healthy and eligible

Worker cleanup result:

- `spot-worker-01` home legacy artifacts archived under `/home/ogre/archive/legacy-worker01-20260424T165738Z`
- `spot-worker-02` home legacy artifacts archived under `/home/ogre/archive/legacy-worker02-20260424T164959Z`
- `spot-worker-03` obvious junk archived under `/home/ogre/archive/legacy-worker03-20260424T165528Z`
- `spot-worker-04` inspected and left alone because it was already minimal

Disabled legacy services:

- `spot-worker-02` legacy services were backed up, stopped, and disabled:
  - `spot-worker6.service`
  - `spot-worker8.service`
  - `m5-worker.service`
  - `spot-avatar.service`
- `spot-worker-03` legacy services were backed up, stopped, and disabled:
  - `spot-worker2.service`
  - `spot-worker3.service`

Worker-01 archived home artifacts:

- `auto_exec.sh`
- `cluster_bundle`
- `fleet-backup.sh`
- `spot-AI`
- `SPOT_GPU_SCHEDULER.md`
- `spot-stack`
- `spot-write-test.txt`
- `starfleet_audit.sh`

Worker-02 archived home artifacts:

- `audit_-5.txt`
- `backup-spot-repo.sh`
- `bootstrap_spot_worker.sh`
- `bootstrap_spot_worker_dual.sh`
- `cluster_bundle`
- `fix-docker-iptables.sh`
- `install-nvidia-container-toolkit.sh`
- `m5-install.sh`
- `m5_setup_spot_avatar.sh`
- `packages.txt`
- `piper-voices`
- `spot-agent`
- `starfleet_audit.sh`
- `target`
- `stack/ollama`
- `.starfleet-stage`

Worker-03 archived home artifacts:

- `backup-spot-repo.sh`
- `codex_worker03_install.sh`
- `packages.txt`
- `pci -nnk -s 05:00.0`

Worker-04 retained intentionally:

- `gpu-burn`
- `install_fleet_models.sh`
- `spot-worker-backup.sh`
- SSH and normal user dotfiles

Current worker-specific notes:

- worker-01 still has `.git-credentials`; do not print it. Handle only through secret-safe policy later.
- worker-01 still has `snap/tree`; harmless.
- worker-02 still has `.docker`, `snap`, empty/top-level `stack`, storage bootstrap scripts, `fleet-inventory`, `install_fleet_models.sh`, and `spot-worker-backup.sh`.
- worker-02 Docker executable was previously confirmed as `/snap/bin/docker`; `docker.service` was not found.
- worker-02 active Ollama is systemd-owned through `/etc/systemd/system/ollama.service`, not compose-owned.
- worker-03 intentionally remains the Codex/dev node and keeps `.codex`, `codex_spot.sh`, `codex-workspace`, `spot-stack`, `.starfleet-stage`, npm/node state, SSH state, and backup/model helper scripts.
- worker-04 is already clean and remains the heavy GPU node.

Validation after cleanup batch:

```text
spot validate:       RESULT: PASS (20 checks, 0 warnings)
spot validate-smoke: RESULT: PASS (26 checks, 0 warnings)
```

Important conclusion:

- current Spot Core does not depend on the disabled legacy per-GPU worker services
- current Spot Core does not depend on archived worker home legacy artifacts
- cleanup did not break current Spot validation or smoke validation
- do not delete archives, disabled service files, `/opt/spot-worker*`, `/etc/spot-workers`, snap Docker, or credentials yet
- keep disabled services and archived artifacts available for rollback during burn-in

### Worker-02 GPU and utility status

`spot-worker-02` remains the owned `utility` worker. Do not change routing ownership unless explicitly requested.

Hardware:

- GPU0: Quadro M4000 8 GB
- GPU1: GTX 1060 6 GB

Intended hardware role:

- GPU0 / Quadro M4000 8GB: utility/light runner through Ollama
- GPU1 / GTX 1060 6GB: monitoring/watch/camera/network workloads when added

Current confirmed runtime:

- Ollama is pinned by UUID to the Quadro M4000:
  - `CUDA_VISIBLE_DEVICES=GPU-df37cf4b-9f71-6aa8-43b7-ab55693fdef1`
- previous numeric pin `CUDA_VISIBLE_DEVICES=0` loaded `phi3.5:latest` onto physical GPU1 / GTX 1060, so numeric pinning should not be used on worker-02
- live Ollama override: `/etc/systemd/system/ollama.service.d/gpu.conf`
- utility model: `phi3.5:latest`
- direct test after UUID pin showed `phi3.5:latest` loaded on GPU0 / Quadro with about 4085 MiB used
- same test showed GPU1 / GTX 1060 essentially idle at about 2 MiB used
- Spot-routed utility request returned through `spot-worker-02` and used the correct utility model
- validation and smoke validation passed after the UUID pin

Warm-policy tuning:

- config file changed: `/home/ogre/spot-stack/spot-core/config/cluster_config.json`
- `warm_model_policy.recent_roles` now includes `utility`
- `warm_model_policy.targets` now includes:

```json
{
  "worker": "spot-worker-02",
  "model": "phi3.5:latest",
  "reason": "utility_primary"
}
```

Confirmed utility latency behavior after restart:

- first post-restart request paid cold load:
  - total duration about 2.08s
  - load duration about 1.14s
- second request while warm improved sharply:
  - total duration about 0.48s
  - load duration about 0.08s
- post-test `nvidia-smi` showed Ollama resident on GPU0 / Quadro at about 4080 MiB
- GPU1 / GTX 1060 remained idle, preserving it for future monitoring/watch use

Known caveat:

- `phi3.5:latest` can still be somewhat verbose for strict utility prompts
- this is now model/prompt behavior, not routing, GPU placement, or warm-policy failure
- future improvement may be prompt shaping or a smaller stricter utility model

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
- `spot_save` reports latest worker backup timestamps
- `spot validate` checks backup freshness and reports PASS/WARN lines before summary
- validator freshness threshold defaults to 8 hours through `SPOT_BACKUP_MAX_AGE_HOURS`

Manual verification completed:

- `spot-worker-01` backup complete
- `spot-worker-02` backup complete
- `spot-worker-03` backup complete
- `spot-worker-04` backup complete

Latest validator freshness result:

```text
RESULT: PASS (20 checks, 0 warnings)
```

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

- decide long-term Unimatrix6 vs `/mnt/collective` strategy
- decide model blob backup policy
- later consider making stale backups fail validation after warning-only period

### Audit write failure logging

Routing audit write failure hardening is implemented in `spotcore/app.py`.

Current behavior:

- `append_routing_audit()` always appends to in-memory `RECENT_ROUTING_AUDIT`
- persistent JSONL write is wrapped in `try/except`
- failures are logged with `LOGGER.exception`
- log message includes:
  - routing audit path
  - timestamp
  - role
  - status
  - worker
  - exception detail

Implementation marker:

```text
routing_audit_write_failed path=%s ts=%s role=%s status=%s worker=%s error=%r
```

This satisfies the roadmap requirement that routing-audit persistence failures are explicit and visible.

### Validator secret-regression scan

The validator now checks tracked files for hardcoded `SPOTCORE_ADMIN_API_TOKEN` assignments without printing secret values.

Current behavior:

- implemented in `watch/fleet-validate.sh`
- uses `git grep` against tracked files
- excludes ignored `.env` files
- redacts any matched value before verbose output
- passes clean in normal validation and smoke validation

Latest verified result:

```text
spot validate:       RESULT: PASS (20 checks, 0 warnings)
spot validate-smoke: RESULT: PASS (26 checks, 0 warnings)
```

Commit:

```text
5949ed7 validate: add secret regression check
```

## Latest confirmed hardening milestone

Latest verified hardening work:

- restart verification hardening
- legacy mutating route deprecation markers
- ownership-first routing fix
- admin token moved out of tracked compose into ignored env file
- `spot_save` worker backup visibility
- `spot validate` worker backup freshness check
- routing audit write failure logging confirmed implemented
- validator secret-regression scan added and confirmed clean
- worker cleanup audit completed for first pass
- legacy worker services disabled on worker-02 and worker-03 after backup
- worker home cleanup/archive pass completed on worker-01, worker-02, and worker-03
- worker-04 inspected and left alone because it was already clean
- final fleet sanity scan confirms all workers are Ollama-only at runtime
- worker-02 UUID GPU pin corrected utility placement to Quadro M4000
- utility warm policy added worker-02 `phi3.5:latest`
- post-tuning smoke validation confirmed clean

Validation after latest checks:

```text
spot validate:       RESULT: PASS (20 checks, 0 warnings)
spot validate-smoke: RESULT: PASS (26 checks, 0 warnings)
```

Confirmed ownership routes after the fix:

- `general -> spot-worker-01`
- `coding -> spot-worker-03`
- `heavy -> spot-worker-04`
- `utility -> spot-worker-02`

## Current next objective

### Primary next objective

Continue Stage 2 cleanup/tuning now that core behavior, smoke validation, audit logging, validator secret-regression scanning, worker cleanup, worker-02 GPU pinning, worker-03 Codex/Git, and worker config backups are proven.

This means:

1. checkpoint this STATE update plus `cluster_config.json` warm-policy change
2. burn in the disabled worker-02 and worker-03 legacy services plus archived worker home artifacts without deleting anything yet
3. observe worker-02 utility latency over more samples after warm-policy change
4. decide whether `phi3.5:latest` needs prompt shaping or replacement for stricter utility responses
5. keep snap Docker and `.git-credentials` untouched until explicit Docker/secrets policy is decided
6. clean up repo/runtime hygiene and document live files versus leftovers
7. decide whether to split read-only MCP and admin MCP into separate wrappers/connectors
8. decide whether `warmd.py` should be wired into runtime lifecycle or explicitly marked dormant

Recommended next target:

```text
checkpoint worker cleanup, worker-02 UUID GPU pin, and utility warm-policy tuning
```

Reason:

- worker cleanup is good enough for burn-in
- worker-02 now matches the intended hardware split
- utility warm behavior is proven with second-call latency around 0.48s
- system-level deletion can wait because disabled services and archives are rollback material

## Do not do next

- do not redesign scheduler routing beyond the ownership-first fix unless a new verified bug appears
- do not change role ownership
- do not rip out the current MCP stack just because Developer Mode is annoying
- do not weaken backup/verification behavior
- do not assume helper scripts are dead without checking runtime use first
- do not conflate ChatGPT platform limits with Spot server bugs
- do not casually change request/response formats
- do not introduce new auth patterns without explicit security design
- do not switch worker-02 back to numeric GPU pinning
- do not delete worker archives until burn-in and archive policy are decided
- do not delete worker-02/worker-03 legacy service files until burn-in and another validation checkpoint confirm they are unnecessary
- do not remove snap Docker until Docker policy is decided
- do not print or casually inspect `.git-credentials`

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
- spot validate-smoke
- spot_save
- ownership-first routing
- legacy mutating route deprecation metadata
- audit write failure logging
- validator secret-regression scan
- worker cleanup audit first pass
- worker-02 legacy services disabled without breaking Spot
- worker-03 legacy services disabled without breaking Spot
- worker-01 home legacy artifacts archived without breaking Spot
- worker-02 home legacy artifacts archived without breaking Spot
- worker-03 obvious junk archived without breaking Spot
- worker-04 inspected and already clean
- final worker runtime shape is Ollama-only on port `11434`
- worker-02 UUID GPU pin places utility/light runner on Quadro M4000 8GB
- worker-02 GTX 1060 6GB is free for future monitoring/watch/camera workloads
- worker-02 utility warm-policy target is active in config
- worker-02 warm utility second-call latency observed around 0.48s
- worker-03 Git/Codex workflow
- worker config backups manually verified on all four AI workers
- worker config backups scheduled every 6 hours
- worker backup script source-controlled
- worker backup visibility in `spot_save`
- worker backup freshness in `spot validate`
- admin token removed from tracked compose and loaded from ignored env file

### Confirmed still rough

- disabled legacy worker-service files still exist and need burn-in before archive/delete
- worker archives exist and need burn-in/archive policy before deletion
- worker-01 `.git-credentials` requires secret-safe handling later
- worker-02 retained snap Docker needs Docker policy decision
- worker-02 retained storage bootstrap scripts need long-term storage policy decision
- `phi3.5:latest` can still be chatty for strict utility prompts
- full API surface cleanup is not complete
- secret/config hygiene is improved but not final
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
- show worker backup state during handoff
- warn about stale worker backups during validation
- avoid storing the admin token directly in tracked compose
- explicitly log routing-audit write failures
- scan tracked files for admin-token regression
- run current Spot successfully without legacy worker-side per-GPU services on worker-02 and worker-03
- run current Spot successfully after worker home archive cleanup
- operate workers as Ollama-only runtime nodes on port `11434`
- run worker-02 utility workloads on the intended Quadro GPU while preserving the GTX 1060 for future monitoring
- keep the worker-02 utility model warm for much lower follow-up latency

The next phase is not rescue. It is hardening and cleanup.
