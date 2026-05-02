# SPOT FLEET STATE

## 2026-05-01 Runtime-aligned checkpoint

This file reflects the current runtime state of the Spot / Starfleet project after assistant-client, memory, supervised apply-plan, and watcher/heartbeat work.

Canonical rules remain in:

- `/home/ogre/spot-stack/HANDOFF.md`
- `/home/ogre/spot-stack/Spot_Autonomy_Policy`
- `/home/ogre/spot-stack/HANDOFF-CODEX-INTEGRATION.md`
- `/home/ogre/spot-stack/HANDOFF-SPOT-INTEGRATION.md`

Roadmap truth lives in:

- `/home/ogre/spot-stack/ROADMAP.md`

---

## Current verified system health

Latest verified state from 2026-05-01:

- Spot Core `/health` is OK.
- `bash /home/ogre/spot-stack/watch/fleet-validate.sh` returned `RESULT: PASS`.
- latest validation summary observed: `pass=19 warn=0 fail=0`.
- all four workers are healthy, eligible, not quarantined, and not degraded.
- routing audit remains clean: `violations=0`, `fallbacks=0`, `manual_overrides=0`.
- worker backups are current and reported OK by `spot_save`.
- Docker `spot-core` is up.
- MCP and Cloudflare tunnel services are active.

Important nuance:

- Fleet validation is PASS.
- `/operator/readiness` may still report `ready_with_warnings` when worker-02 utility latency exceeds readiness threshold.
- This is expected and is not a validator failure.

Current known warning/debt:

- worker: `spot-worker-02`
- condition: utility lane latency remains high
- recent observed values: p50 around 7.6-8.2s, average around 10.7-11.1s, around 26-27 tok/sec

---

## Phase 1 — Spot Operator Ready status

Status: **complete for current scope**.

Completed/live:

- standardized operator command surface via `spot-ops.sh`
- MCP operator command surface for safe read/validation commands
- live `/operator/readiness` endpoint
- live `/health`, `/routing`, `/fleet/ping`, `/stats/latency`, `/stats/routing-audit`
- backup-first enforcement remains in Spot Core mutation wrappers
- read-only operator command risk classification is low risk
- fleet validator passes cleanly

Known remaining Phase 1 debt:

- worker-02 utility latency remains warning-level
- worker-02 and worker-03 multi-GPU hosts still need true GPU-pinned Ollama service separation before config lane labels can be fully trusted

---

## Phase 1.5 — Spot Assistant Client Surface status

Status: **mostly complete; active maturation continues**.

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
- `spot generate-patch` legacy alias
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
- injects durable memory and related historical proposal/apply-plan context when relevant
- enforces canonical path guidance
- warns on forbidden invented paths/services such as `spot-client.service`, `spot-ops.service`, `/etc/config/worker-02.yaml`, and `/home/ogre/spot-stack/bin/spot`
- can save proposal markdown artifacts under `/home/ogre/spot-stack/watch/proposals`

Proposal lifecycle current behavior:

- saved proposals begin as `pending_review`
- `spot approve <proposal>` marks a proposal approved and records durable memory entries
- `spot reject <proposal>` marks a proposal rejected
- `spot proposal-status <proposal>` prints lifecycle metadata

---

## Phase 1.6 — Persistent Memory Foundation status

Status: **base layer live**.

Current memory backend:

- `/mnt/collective/spot/memory`

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

Memory informs context. Memory is not authorization.

---

## Phase 1.7 — Supervised Apply-Plan Engine status

Status: **current active lane**.

Purpose:

- bridge proposal-only planning to future controlled mutation
- create specific reviewable apply-plan artifacts
- preserve backup-first, validation-first, rollback-first policy
- keep mutation disabled until a future Spot Core controlled execution wrapper exists

Live commands:

- `spot generate-apply-plan <approved-proposal>`
- `spot apply-plans [count]`
- `spot show-apply-plan <apply-plan>`
- `spot apply-plan-status <apply-plan>`
- `spot apply-plan-check <apply-plan>`
- `spot apply-plan-verify <apply-plan>`
- `spot approve-apply-plan <apply-plan>`
- `spot reject-apply-plan <apply-plan>`
- `spot prepare-execution-handoff <apply-plan>`
- `spot execution-handoffs [count]`
- `spot show-execution-handoff <execution-handoff>`
- `spot execution-handoff-status <execution-handoff>`
- `spot execution-handoff-verify <execution-handoff>`
- `spot generate-patch <approved-proposal>` legacy alias to supervised apply-plan generation

Current behavior:

- apply-plan generation is blocked unless the linked proposal is approved
- apply-plan artifacts are written under `/home/ogre/spot-stack/watch/apply-plans`
- generated artifacts include target files, risk class, pre-change backup requirements, precheck validation, planned mutations, post-apply validation, rollback plan, human review gate, and non-mutating notes
- proposal-provided validation augments the default required validation set instead of replacing it
- `apply-plan-check` validates pending review artifacts only
- `apply-plan-verify` accepts `pending_manual_review` and `review_approved`
- `approve-apply-plan` marks `apply_status: review_approved` and adds `review_approved_utc`
- `reject-apply-plan` marks `apply_status: review_rejected` and adds `review_rejected_utc`
- reviewed apply-plans can generate non-mutating execution handoff artifacts
- execution handoffs can be listed, shown, summarized, and verified
- execution handoffs explicitly keep `execution_allowed: false`
- lifecycle changes keep `mutation_allowed: false`

Verified apply-plan example:

- proposal: `P-20260501-133615-revise-routing-so-utility-role-remains-primary-o`
- apply-plan: `APPLY-P-20260501-133615-revise-routing-so-utility-role-remains-primary-o`
- status: `review_approved`
- verification: `spot apply-plan-verify ...` returned `RESULT: PASS status=review_approved fail=0 warn=0`
- mutation flag: `mutation_allowed: false`

Current non-goals:

- no unrestricted auto-apply
- no direct config mutation from client scripts
- no bypassing backup-first enforcement
- no high-risk network/firewall/DNS/DHCP/VLAN/routing mutation outside narrow approved endpoints

Remaining Phase 1.7 work before Phase 2:

1. document/apply policy classification on apply-plan artifacts if not already explicit enough
2. add backup binding/checkpoint reference design for future execution
3. define controlled handoff from `review_approved` apply-plan to future Spot Core execution wrapper
4. update docs and checkpoints after meaningful slices only

---

## Active watcher / heartbeat status

Spot has an active heartbeat/watch stack.

Active timers observed:

- user timer: `fleet-watch.timer` every 2 minutes
- user timer: `fleet-remediate.timer` every 5 minutes
- system timer: `spot-monitor-alert-state.timer` every 1 minute
- system timer: `spot-monitor-snapshot.timer` every 5 minutes

Services/scripts:

- `/home/ogre/spot-stack/watch/fleet-watch.sh`
- `/home/ogre/spot-stack/watch/fleet-remediate.sh`
- `/home/ogre/spot-stack/watch/fleet-monitor-snapshot.sh`

Monitor state/log paths:

- `/home/ogre/spot-stack/watch/logs/fleet-watch.log`
- `/home/ogre/spot-stack/watch/logs/fleet-remediate.log`
- `/home/ogre/spot-stack/watch/state/remediation-state.json`
- `/home/ogre/spot-stack/watch/state/history/monitor-summary.jsonl`
- `/home/ogre/spot-stack/watch/state/history/monitor-alert-latest.json`
- `/home/ogre/spot-stack/watch/state/history/monitor-alert-transitions.jsonl`
- `/home/ogre/spot-stack/watch/state/history/snapshots/`

Snapshot repair completed:

- `spot-monitor-snapshot.service` was failing because `/home/ogre/spot-stack/watch/state/history/snapshots` lacked directory execute permission.
- Fix applied: `chmod 755 /home/ogre/spot-stack/watch/state/history/snapshots`.
- `sudo systemctl start spot-monitor-snapshot.service` then completed with status `0/SUCCESS`.
- fresh snapshot observed: `/home/ogre/spot-stack/watch/state/history/snapshots/2026-05-01-1777664884.json`.
- fresh monitor summary showed health/routing/workers/endpoints/DNS/network all OK.

Interpretation:

- monitoring and alert-state plumbing exists and is active
- remediation timer exists and records remediation-state backups
- full Phase 2 autonomous incident/remediation loop is not active yet

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

Current assistant/apply-plan layer is proposal-first and review-first. It does not bypass Spot Core mutation policy.

---

## Current active lane

Current active lane:

**Phase 1.7 — supervised apply-plan engine and controlled execution preparation.**

The next major roadmap phase after Phase 1.7 is Phase 2 — Build Spot Controlled Autonomy.

There is currently no documented Phase 1.8.

Immediate next work should focus on:

1. finishing Phase 1.7 artifact semantics and execution handoff design
2. keeping watcher/heartbeat state healthy
3. preparing Phase 2 incident/remediation flow from existing monitor timers
4. ensuring future mutation remains backup-first, verified, logged, and routed through Spot Core enforcement

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
spot apply-plan-verify APPLY-P-20260501-133615-revise-routing-so-utility-role-remains-primary-o
spot ask "what is the current fleet status"
spot memory 20
systemctl status spot-monitor-snapshot.service --no-pager --full
```

---

## Historical note

Older STATE.md content before this checkpoint stopped around Milestone B / early Phase 1.5 and did not reflect the completed D.1-D.5b assistant and memory work or the Phase 1.7 apply-plan lifecycle. This checkpoint supersedes that stale state while preserving the locked rules in HANDOFF.md and Spot Autonomy Policy.
