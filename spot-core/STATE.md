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

This is no longer a theory stack. It is a live operational control surface.


### Worker-02 GPU note

- `spot-worker-02` remains the owned `utility` worker and routing ownership must not change.
- Hardware on `spot-worker-02`: `GPU0 Quadro M4000 8GB`, `GPU1 GTX 1060 6GB`.
- Live Ollama systemd override currently sets `CUDA_VISIBLE_DEVICES=0`.
- Despite that override, after warm utility calls `nvidia-smi` showed the Quadro idle and the GTX 1060 using about `3730 MiB`, so `phi3.5:latest` is effectively loading on the GTX 1060 in current runtime behavior.
- Worker health is good, but `utility` responses can still be slow or overly verbose, especially from cold starts.
- Any live worker override changes must be backed up separately: `spot_save` captures repo/runtime handoff state but does not capture `/etc/systemd` overrides on workers.
- No scripts have been added yet for this issue.

## Current active to-do list

Current priority order:

1. Finish the current hardening thread already in progress.
2. Finish worker-02 issue: document and stabilize the Ollama GPU behavior/pinning decision.
3. Finish worker-03 issue: Codex works locally, GitHub access is fixed, and the live `spot-stack` repo is cloned on worker-03.
4. Fix backup reality: workers are not currently being automatically backed up to Unimatrix6/backup storage.
5. After those are clean, return to broader Stage 2 cleanup.

### Worker-02 pending item

Worker-02 has two GPUs:

- GPU0: Quadro M4000 8 GB
- GPU1: GTX 1060 6 GB

Current observed behavior:

- Ollama utility role uses `phi3.5:latest`
- utility route is healthy but can be slow, especially on cold start
- live override is `/etc/systemd/system/ollama.service.d/gpu.conf`
- live override currently sets `CUDA_VISIBLE_DEVICES=0`
- observed warm runtime loaded `phi3.5:latest` on the GTX 1060
- `spot validate` passed clean after confirming the override

Pending:

- capture worker-02 service override in backup/state so it is not lost
- keep routing ownership unchanged
- decide later whether `phi3.5:latest` should be replaced due to verbosity

### Worker-03 pending item

Worker-03 has Codex CLI/tooling installed and usable.

Confirmed:

- Codex updated to `v0.124.0`
- `codex_spot.sh` launcher works
- `~/.starfleet-stage` is now a Git repo
- Codex created and committed `fleet-docs/WORKSPACE_MAP.md`
- Codex created and committed `fleet-docs/PORTING_NOTES.md`
- GitHub SSH access works
- `/home/ogre/spot-stack` exists on worker-03 and tracks `git@github.com:chrisk-2/spot-AI.git`

Important distinction:

- worker-03 has Codex CLI/tooling installed
- worker-03 does not have a Codex Ollama model
- Codex is for repo/workspace editing, not `/exec` model routing

Pending:

- use worker-03 Codex against the live repo clone for reviewed repo edits only
- do not treat `.starfleet-stage` as live current Spot runtime; it is historical/staging fleet workspace
- inspect/preserve useful `.starfleet-stage` docs/scripts without blindly running old tooling

### Backup / Unimatrix6 pending item

Reality correction:

- `spot_save` backs up/checkpoints the spot-core repo and runtime handoff state
- `spot_save` does not automatically back up each worker filesystem/config
- workers are not currently proven to have automated backup jobs
- `/mnt/collective/backups` exists and is writable from at least worker-03
- `/mnt/unimatrix6` did not show useful output from the quick worker-03 check and still needs direct verification per worker

Pending:

- verify Unimatrix6 mount state on all workers
- define actual backup target path
- create worker config backup script covering systemd overrides, Ollama service config, important `/home/ogre` scripts, crontab/timers, package list, mount state, and selected repo/workspace state
- decide policy for large model data under `/srv/ollama` or equivalent: backup models vs re-pull models
- schedule worker backups via systemd timer or cron
- update `spot_save` to report worker backup freshness/status
- later wire mutating Spot actions to verified pre-change backup enforcement

## Latest confirmed hardening milestone

Latest committed checkpoint after hardening work:

```text
0cac6e9 checkpoint: 2026-04-24-13:54:37
```

Included:

- restart verification hardening
- legacy mutating route deprecation markers
- ownership-first routing fix
- STATE.md update

Validation after patch:

```text
RESULT: PASS (15 checks, 0 warnings)
```

Confirmed ownership routes after the fix:

- `general -> spot-worker-01`
- `coding -> spot-worker-03`
- `heavy -> spot-worker-04`
- `utility -> spot-worker-02`

## Plain-English bottom line

Spot is operationally real, but the worker backup assumption was wrong.

The control-plane repo is being checkpointed by `spot_save`. The workers themselves still need a real backup layer and Unimatrix6/backup-target verification.

Do not start broad new architecture work until worker-02 GPU behavior, worker-03 Git access/Codex workflow, and worker backups are cleaned up.
