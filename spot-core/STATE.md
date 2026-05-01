# SPOT FLEET STATE

## 2026-05-01 Runtime-aligned checkpoint

This file reflects the actual current runtime state of the Spot / Starfleet project after the D.1 through D.5b assistant-client and memory work.

Canonical rules remain in:

- `/home/ogre/spot-stack/HANDOFF.md`
- `/home/ogre/spot-stack/Spot_Autonomy_Policy`
- `/home/ogre/spot-stack/HANDOFF-CODEX-INTEGRATION.md`
- `/home/ogre/spot-stack/HANDOFF-SPOT-INTEGRATION.md`

---

## Current verified system health

Latest operator verification from 2026-05-01:

- `bash /home/ogre/spot-stack/watch/fleet-validate.sh` returned `RESULT: PASS`.
- validation summary: `pass=19 warn=0 fail=0`.
- `spot-ops.sh quick-health` showed core health OK.
- all four workers are healthy, eligible, not quarantined, and not degraded.
- endpoint quick-health summary showed `ok_count=5 fail_count=0`.
- routing audit remains clean: `violations=0`, `fallbacks=0`, `manual_overrides=0`.

MCP/operator verification:

- `admin_operator_command status` works and returns all workers OK.
- `admin_operator_command readiness` works through live `/operator/readiness`.
- MCP `status` reported `Fleet: ALL SYSTEMS NOMINAL`.

Important nuance:

- Fleet validation is PASS.
- `/operator/readiness` still reports `ready_with_warnings` because worker-02 utility latency remains above warning threshold.
- This is expected and is not a validator failure.

Current readiness warning:

- worker: `spot-worker-02`
- condition: p50 latency above 5000ms
- recent observed values: p50 about 7.6s, average about 10.7s, about 26.8 tok/sec

---

## Phase 1 — Spot Operator Ready status

Phase 1 is complete for the current scope.

Completed/live:

- standardized operator command surface via `spot-ops.sh`
- MCP operator command surface for safe read/validation commands
- live `/operator/readiness` endpoint
- live `/health`, `/routing`, `/fleet/ping`, `/stats/latency`, `/stats/routing-audit`
- backup-first enforcement remains in Spot Core mutation wrappers
- read-only operator command risk classification is low risk
- fleet validator currently passes cleanly

Known remaining Phase 1 debt:

- worker-02 utility latency remains warning-level
- worker-02 and worker-03 multi-GPU hosts still need true GPU-pinned Ollama service separation before config lane labels can be fully trusted

---

## Phase 1.5 — Spot Assistant Client Surface status

Phase 1.5 is substantially implemented in the terminal/client layer.

Live client files:

- `/home/ogre/spot-stack/watch/spot-client.sh`
- `/home/ogre/spot-stack/watch/spot-ops.sh`

Live assistant/operator commands:

- `spot ask`
- `spot propose`
- `spot propose --save`
- `spot proposals`
- `spot show-proposal`
- `spot approve`
- `spot reject`
- `spot proposal-status`
- `spot generate-patch`
- `spot remember`
- `spot memory`
- `spot recall`

`spot ask` current behavior:

- routes normal prompts through Spot Core `/exec`
- auto-classifies roles for common general/coding/heavy/utility prompts
- short-circuits live telemetry prompts such as fleet status, routing audit, and latency to live Spot endpoints instead of asking an LLM to guess
- prints route metadata for model/worker visibility
- injects durable memory context when relevant

`spot propose` current behavior:

- proposal-only, no mutation
- uses live Spot context from readiness, latency, and routing audit
- injects durable memory and related historical proposal/patch context when relevant
- enforces canonical path guidance
- warns on forbidden invented paths/services such as `spot-client.service`, `spot-ops.service`, `/etc/config/worker-02.yaml`, and `/home/ogre/spot-stack/bin/spot`
- can save proposal markdown artifacts under `/home/ogre/spot-stack/watch/proposals`

Proposal lifecycle current behavior:

- saved proposals begin as `pending_review`
- `spot approve <proposal>` marks a proposal approved and records durable memory entries
- `spot reject <proposal>` marks a proposal rejected
- `spot proposal-status <proposal>` prints lifecycle metadata

Patch artifact current behavior:

- `spot generate-patch <approved proposal>` requires approved proposal status
- pending or rejected proposals are blocked from patch artifact generation
- generated artifacts are markdown handoff files under `/home/ogre/spot-stack/watch/patches`
- generated patch artifacts currently have `apply_status: pending_manual_apply`
- this does not mutate target config files

Current approved/generated examples observed in memory:

- approved proposal `P-20260501-000539-fix-worker-02-latency`
- patch artifact `PATCH-P-20260501-000539-fix-worker-02-latency`
- approved proposal `P-20260501-133615-revise-routing-so-utility-role-remains-primary-o`
- patch artifact `PATCH-P-20260501-133615-revise-routing-so-utility-role-remains-primary-o`

---

## Persistent memory status

D.5/D.5b memory layer is live.

Current memory backend:

- `/mnt/collective/spot/memory`

This path is on Unimatrix shared storage and is the persistent memory source of truth for the current implementation.

Observed memory files:

- `facts.jsonl`
- `decisions.jsonl`
- `preferences.jsonl`
- `sessions.jsonl`
- `roadmaps.jsonl`

NFS ownership note:

- `/mnt/collective/spot/memory` is mapped to ownership like `1024:users` by the storage export.
- `chown` may return `Operation not permitted`.
- This is not currently a blocker because files are writable through the exported permissions.

Memory commands:

- `spot remember <fact|decision|session|preference|roadmap> <text>` appends durable memory entries
- `spot memory [count]` shows recent durable memory entries
- `spot recall <keyword>` searches durable memory entries

Memory is now used by:

- `spot ask` context injection
- `spot propose` context injection
- proposal approval memory logging
- patch artifact generation memory logging

---

## Current physical GPU map

Current hardware before pending upgrades:

- worker-01: RTX 3060 12GB
- worker-02: Quadro M4000 8GB + GTX 1060 6GB
- worker-03: GTX 1070 8GB + RTX 3060 12GB
- worker-04: Titan Xp 12GB

Pending/future hardware plan:

- Quadro P6000 24GB is expected later.
- Planned placement: P6000 to worker-04 as heavy primary.
- Displaced Titan Xp 12GB should move to worker-02, preferably replacing GTX 1060 6GB.
- If Titan Xp does not physically fit beside M4000, replace M4000 instead and leave GTX 1060 for embeddings/watcher-only use.
- If a second P6000 is acquired, reassess before changing topology.

---

## Current modeled routing debt

Current confirmed debt:

- worker-02 has two physical GPUs but currently functions as one modeled Ollama lane for utility/watcher behavior.
- worker-03 has two physical GPUs and two logical GPU routes, but still one worker-level Ollama base URL.
- Spot can label logical lanes, but cannot guarantee physical GPU selection unless Ollama services are pinned per GPU.

Priority:

1. worker-02 GPU/service isolation is higher priority because it has active utility latency warnings.
2. worker-03 can be deferred because it is currently healthy and acceptable under current load.

Preferred future model:

- use separate pinned Ollama services per GPU when needed
- likely pattern: logical worker/service split such as `spot-worker-02a` and `spot-worker-02b` on distinct ports with `CUDA_VISIBLE_DEVICES` or equivalent pinning
- do not blindly split config lanes until actual GPU order and worker service pinning are verified after hardware changes

---

## Policy posture

Autonomy policy remains locked:

- No backup, no change.
- Detect → Analyze → Classify → Backup → Plan → Verify → Execute → Test/Rollback.
- Spot Core holds mutation authority.
- Clients propose; Spot Core applies through enforced wrappers.
- High-risk firewall/DNS/DHCP/VLAN/routing/OPNsense changes remain gated and require narrow approved endpoints.

Current assistant client layer is proposal-first and does not bypass Spot Core mutation policy.

---

## Current active lane

The project is past Milestone B operator standardization and past the first assistant-client MVP.

Current active lane:

**Phase 1.5 / D.4a — supervised apply-plan engine and controlled execution maturation.**

Immediate next work should focus on:

1. keeping docs aligned with runtime state
2. tightening proposal quality and historical awareness
3. building supervised apply-plan artifacts that remain backup-first and non-mutating until explicitly approved
4. preparing a future controlled apply workflow that routes all mutation through Spot Core enforcement

Do not implement unrestricted auto-apply.
Do not bypass backup-first enforcement.
Do not treat memory as authorization.

---

## Next safe verification commands

Use these before future state changes:

```bash
python3 -m py_compile /home/ogre/spot-stack/spot-core/spotcore/app.py
bash -n /home/ogre/spot-stack/watch/spot-ops.sh
bash -n /home/ogre/spot-stack/watch/spot-client.sh
bash /home/ogre/spot-stack/watch/fleet-validate.sh
bash /home/ogre/spot-stack/watch/spot-ops.sh quick-health
spot ask "what is the current fleet status"
spot memory 20
```

---

## Historical note

Older STATE.md content before this checkpoint stopped around Milestone B / early Phase 1.5 and did not reflect the completed D.1-D.5b assistant and memory work. This checkpoint supersedes that stale state while preserving the locked rules in HANDOFF.md and Spot Autonomy Policy.
