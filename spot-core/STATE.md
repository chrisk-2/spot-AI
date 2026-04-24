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
- admin token was removed from tracked `docker-compose.yml` and is now loaded from ignored `spot-core/.env`
- `spot_save` now shows worker backup status in handoff output
- `spot validate` now checks worker backup freshness
- worker backup freshness threshold defaults to 8 hours via `SPOT_BACKUP_MAX_AGE_HOURS`
- routing audit write failures are explicitly logged with path, timestamp, role, status, worker, and exception detail
- validator secret-regression scan is implemented and confirmed clean
- legacy per-GPU worker services on worker-02 and worker-03 are disabled after backup and validation
- worker-02 home legacy artifacts are archived under `/home/ogre/archive/legacy-worker02-20260424T164959Z`
- worker-02 retained Docker/Ollama/stage leftovers were inspected and classified
- latest normal validation passed with 20 checks and 0 warnings
- latest smoke validation passed with 26 checks and 0 warnings

Latest validation after worker-02 retained-leftover inspection:

```text
spot status:         Fleet ALL SYSTEMS NOMINAL
spot validate:       RESULT: PASS (20 checks, 0 warnings)
spot validate-smoke: RESULT: PASS (26 checks, 0 warnings)
```

Latest checkpoint commit before this cleanup phase:

```text
5949ed7 validate: add secret regression check
```

This is no longer a theory stack. It is a live operational control surface.

## Current worker, Codex, and backup status

### Worker cleanup audit status

A first cleanup inventory was run across all four workers after the hostname/role migration.

Confirmed from audit:

- all four hostnames now match current naming:
  - `spot-worker-01`
  - `spot-worker-02`
  - `spot-worker-03`
  - `spot-worker-04`
- all four workers still have the 6-hour worker config backup cron entry
- all four workers expose Ollama on port `11434`
- current Spot routing still sees all four workers healthy and eligible

Current cleanup result:

- `spot-worker-02` legacy services were backed up, stopped, and disabled:
  - `spot-worker6.service`
  - `spot-worker8.service`
  - `m5-worker.service`
  - `spot-avatar.service`
- `spot-worker-03` legacy services were backed up, stopped, and disabled:
  - `spot-worker2.service`
  - `spot-worker3.service`
- after disable, worker-02 only showed Ollama listening on `11434` from the checked legacy/runtime ports
- after disable, worker-03 only showed Ollama listening on `11434` from the checked legacy/runtime ports
- worker-02 home legacy artifacts were moved into `/home/ogre/archive/legacy-worker02-20260424T164959Z`
- post-archive `spot validate` passed with 20 checks and 0 warnings
- post-archive `spot validate-smoke` passed with 26 checks and 0 warnings
- post-inspection `spot status` reported Fleet ALL SYSTEMS NOMINAL

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

Worker-02 retained-leftover inspection:

- Docker executable is `/snap/bin/docker`
- `snap list docker` reports docker `28.4.0` rev `3377` from `latest/stable`
- `systemctl status docker` reports `Unit docker.service could not be found`
- worker-02 current Ollama runtime is systemd-owned through `/etc/systemd/system/ollama.service`
- worker-02 Ollama is active and enabled
- Ollama drop-ins are:
  - `/etc/systemd/system/ollama.service.d/gpu.conf`
  - `/etc/systemd/system/ollama.service.d/override.conf`
- Ollama runtime env includes:
  - `CUDA_VISIBLE_DEVICES=0`
  - `OLLAMA_HOST=0.0.0.0:11434`
  - `OLLAMA_MODELS=/srv/ollama`
- `/home/ogre/stack/ollama` contains only `compose.yml`
- `/home/ogre/.starfleet-stage` is small, about 164K

Worker-02 retained classification:

- `/home/ogre/spot-worker-backup.sh`: KEEP, current backup system depends on it
- `/home/ogre/fleet-inventory`: KEEP, current runtime/GPU evidence
- `/home/ogre/install_fleet_models.sh`: KEEP for now, useful model helper
- `/home/ogre/bootstrap_mount_unimatrix6_nfs.sh`: KEEP/CHECK, storage bootstrap reference
- `/home/ogre/fleet_storage_bootstrap.sh`: KEEP/CHECK, storage bootstrap reference
- `/home/ogre/stack/ollama`: ARCHIVE candidate, because active Ollama is systemd-owned and only `compose.yml` remains there
- `/home/ogre/.starfleet-stage`: ARCHIVE candidate, tiny staged workspace not shown as current runtime dependency on worker-02
- `/home/ogre/snap/docker`: CHECK before removal, because Docker comes from snap but no docker.service exists; do not remove snap Docker without deciding Docker policy
- shell, SSH, Docker, NVIDIA, local, and cache/user dotfiles: KEEP/IGNORE unless specific cleanup need appears

Important conclusion:

- current Spot Core does not depend on the disabled legacy per-GPU worker services
- worker-02 home cleanup did not break current Spot validation or smoke validation
- worker-02 active Ollama is systemd-owned, not `/home/ogre/stack/ollama` compose-owned
- do not delete unit files, `/opt/spot-worker*`, `/etc/spot-workers`, archived worker-02 artifacts, snap Docker, or retained storage/runtime helpers yet
- keep disabled services and archived artifacts available for rollback during burn-in
- next cleanup phase can safely archive `/home/ogre/stack/ollama` and maybe `/home/ogre/.starfleet-stage` after one more validation if desired

### Worker-02 GPU status

`spot-worker-02` remains the owned `utility` worker. Do not change routing ownership unless explicitly requested.

Hardware:

- GPU0: Quadro M4000 8 GB
- GPU1: GTX 1060 6 GB

Current confirmed runtime:

- both `ollama serve` and `ollama runner` inherit `CUDA_VISIBLE_DEVICES=0`
- despite that, `nvidia-smi` reports the runner on physical GPU 1 / GTX 1060
- therefore CUDA-visible index 0 maps to the GTX 1060 in the current Ollama runtime context
- this is not a Spot routing failure
- current safest action is to document the effective mapping and avoid changing GPU pinning until there is a concrete need
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

Current Codex investigation read:

- this is not proven to be a routing failure
- likely contributors are CUDA device-numbering ambiguity, Ollama runtime placement behavior, cold-start behavior, and `phi3.5:latest` verbosity
- current warm policy does not include `utility`, so utility cold-start remains plausible
- `spot validate` proves route/API ownership, not definitive GPU placement
- safest next step is a controlled manual test on worker-02 with service restart, one utility call, and immediate `nvidia-smi`/process inspection before changing config

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
- worker-02 home legacy artifacts archived
- worker-02 retained Docker/Ollama/stage leftovers inspected and classified
- post-archive smoke validation confirmed clean

Validation after latest checks:

```text
spot status:         Fleet ALL SYSTEMS NOMINAL
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

Continue Stage 2 cleanup now that core behavior, smoke validation, audit logging, validator secret-regression scanning, worker-02 GPU state, worker-03 Codex/Git, worker config backups, first-pass worker legacy-service cleanup, worker-02 home artifact archive, and worker-02 retained-leftover inspection are proven.

This means:

1. checkpoint this STATE update and current clean validation state
2. burn in the disabled worker-02 and worker-03 legacy services plus worker-02 archived home artifacts without deleting anything yet
3. optionally archive worker-02 `/home/ogre/stack/ollama` and `/home/ogre/.starfleet-stage`, then validate
4. keep snap Docker until Docker policy is decided
5. perform controlled worker-02 manual tests before changing GPU pinning, model selection, or warm policy
6. clean up repo/runtime hygiene and document live files versus leftovers
7. decide whether to split read-only MCP and admin MCP into separate wrappers/connectors
8. decide whether `warmd.py` should be wired into runtime lifecycle or explicitly marked dormant

Recommended next target:

```text
checkpoint worker-02 retained-leftover inspection, then decide small archive of stack/ollama and .starfleet-stage or move to worker-02 GPU test
```

Reason:

- worker-02 active Ollama is systemd-owned and not using `/home/ogre/stack/ollama`
- worker-02 `.starfleet-stage` is tiny and not shown as runtime-critical
- Docker is snap-installed and should not be removed until Docker policy is decided
- worker-02 remains the main runtime behavior uncertainty because of GPU mapping, cold-start behavior, and `phi3.5:latest` verbosity

## Do not do next

- do not redesign scheduler routing beyond the ownership-first fix unless a new verified bug appears
- do not change role ownership
- do not rip out the current MCP stack just because Developer Mode is annoying
- do not weaken backup/verification behavior
- do not assume helper scripts are dead without checking runtime use first
- do not conflate ChatGPT platform limits with Spot server bugs
- do not casually change request/response formats
- do not introduce new auth patterns without explicit security design
- do not change worker-02 GPU pinning, warm policy, or utility model until a controlled test proves the issue
- do not delete worker-02/worker-03 legacy service files until burn-in and another validation checkpoint confirm they are unnecessary
- do not delete worker-02 archived artifacts until burn-in and archive policy are decided
- do not remove snap Docker on worker-02 until Docker policy is decided

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
- worker-02 home legacy artifacts archived without breaking Spot
- worker-02 retained Docker/Ollama/stage leftovers classified
- worker-02 GPU override documented and inventoried
- worker-03 Git/Codex workflow
- worker config backups manually verified on all four AI workers
- worker config backups scheduled every 6 hours
- worker backup script source-controlled
- worker backup visibility in `spot_save`
- worker backup freshness in `spot validate`
- admin token removed from tracked compose and loaded from ignored env file

### Confirmed still rough

- disabled legacy worker-service files still exist and need burn-in before archive/delete
- worker-02 archive exists and needs burn-in/archive policy before deletion
- worker-02 retained snap Docker needs Docker policy decision
- worker-02 retained `stack/ollama` and `.starfleet-stage` are archive candidates
- full API surface cleanup is not complete
- secret/config hygiene is improved but not final
- helper-script/live-file clarity
- Developer Mode dependency for custom MCP usage in ChatGPT
- warmd lifecycle decision
- final operator UI polish
- worker-02 GPU/model/cold-start behavior needs controlled testing

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
- run current Spot successfully after archiving worker-02 home legacy artifacts

The next phase is not rescue. It is hardening and cleanup.
