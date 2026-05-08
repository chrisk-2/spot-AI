# SPOT CORE STATE — 2026-05-05

## CURRENT STATUS

Spot Core stable.
Fleet validation passing.
Primary routing ownership intact.
Git tree clean at last checkpoint.

Current commit:
- e549460 codex: add non-mutating task artifact layer

Validation baseline:
- spot validate: PASS
- pass=19
- warn=0
- fail=0

Runtime health:
- spot-core OK
- worker backups OK for spot-worker-01 through spot-worker-04

Known condition:
- spot-worker-02 remains healthy but slow on the utility lane.
- Do not tune worker-02 until after the planned GPU reshuffle unless a new hard failure appears.

---

## CURRENT ACTIVE LANE

PHASE 2 — BUILD SPOT CONTROLLED AUTONOMY

Status: ACTIVE, NON-MUTATING CONTROL STACK BASELINE THROUGH PHASE 2.31

Immediate next active step while waiting for worker-04 GPU hardware:

PHASE 2.31 — NON-MUTATING TASK ARTIFACT LAYER

Goal:
- Continue completing Phase 2 control-plane work.
- Do not route worker-05 automatically.
- Do not modify production routing until a separate reviewed routing slice.

Current safety posture:
- mutation_plugins_enabled: false
- plugin_execution_enabled: false
- plugin_execution_allowed: false
- execution_allowed remains false in generated control artifacts
- mutation_allowed remains false in generated control artifacts
- mutation_performed remains false in generated control artifacts
- backup delete/overwrite remains forbidden
- freeform shell mutation remains forbidden
- high-risk network change remains restricted/disabled or forbidden depending layer
- no backup, no change remains absolute
- immutable executor journal active
- executor journal append/list/verify/summary active
- executor journal remains audit-only
- executor journal cannot trigger execution or mutation
- non-mutating task artifact layer active
- task create/list/show/verify/summary active
- task artifacts remain proposal-only
- task artifacts cannot independently trigger execution or mutation

---

## COMPLETED PHASE 2 SLICES

- Phase 2.1 — Execution-run lifecycle
- Phase 2.2 — Execution-run read-only visibility
- Phase 2.3 — Action policy manifest
- Phase 2.4 — Action policy verifier
- Phase 2.5 — Non-executing action request artifacts
- Phase 2.6 — Action request lifecycle
- Phase 2.7 — Action request audit/summary
- Phase 2.8 — Non-executing action handoff bridge
- Phase 2.9 — Action handoff lifecycle/audit
- Phase 2.10 — Disabled plugin registry manifest
- Phase 2.11 — Plugin registry audit/summary
- Phase 2.12 — Non-executing plugin request artifacts
- Phase 2.13 — Plugin request lifecycle/audit
- Phase 2.14 — Executor dry-run preflight contract
- Phase 2.15 — Executor preflight lifecycle/operator surface
- Phase 2.16 — Executor preflight failure-path validation
- Phase 2.18 — Backup-binding contract design
- Phase 2.19 — Backup-binding contract operator surface
- Phase 2.20 — Backup-binding contract summary/failure validation
- Phase 2.22 — Backup artifact manifest contract design
- Phase 2.23 — Backup artifact manifest operator surface
- Phase 2.24 — Backup artifact manifest summary/failure validation
- Phase 2.26 — Backup artifact manifest implementation dry-run simulator
- Phase 2.27 — Backup artifact manifest dry-run operator surface
- Phase 2.28 — Backup artifact manifest dry-run summary/failure validation
- Phase 2.30 — Immutable executor journal
- Phase 2.31 — Non-mutating task artifact layer

---

## CURRENT CONTROL STACK

Current non-executing control chain:

1. Action policy manifest
2. Action policy verifier
3. Action request artifact
4. Action request verifier
5. Action request lifecycle
6. Action request audit/summary
7. Action handoff candidate
8. Action handoff verifier
9. Action handoff lifecycle
10. Action handoff audit/summary
11. Plugin registry manifest
12. Plugin registry verifier
13. Plugin registry audit/summary
14. Plugin request artifact
15. Plugin request verifier
16. Plugin request lifecycle
17. Plugin request audit/summary
18. Executor dry-run preflight contract
19. Executor preflight lifecycle/operator surface
20. Executor preflight failure-path validation
21. Backup-binding contract design
22. Backup-binding contract operator surface/summary
23. Backup-binding contract failure-path validation
24. Backup artifact manifest contract design
25. Backup artifact manifest operator surface/summary
26. Backup artifact manifest failure-path validation
27. Backup artifact manifest dry-run simulator
28. Backup artifact manifest dry-run operator surface/summary
29. Backup artifact manifest dry-run failure-path validation
30. Immutable executor journal
31. Non-mutating task artifact layer

This is a control and audit stack only.
It does not dispatch plugins.
It does not mutate live systems.
It does not bind backups for mutation.
It does not enable autonomous execution.
It records executor contract verification/task events only.
It does not trigger execution from journal events.
It does not modify live runtime files.
Task artifacts represent proposed work only.
Task artifacts are not execution authorization.
Task artifacts cannot independently dispatch workers or apply runtime changes.

---

## WORKER-05 STATUS

worker-05 integration status:
- validated
- documented
- inventory-registered
- standby-guarded
- manual-ask capable
- future-registration drafted
- not production-routed

Current worker-05 classification:

```text
worker-05 = heavy-secondary / standby / burst-candidate / fallback-candidate
routing_enabled = false
primary = false
production_role = none
```

Latest worker-05 checkpoint:
- 60daec0 worker05: add guarded standby registration draft

Worker-05 artifacts:
- /home/ogre/spot-stack/WORKER-05-COMMISSIONING.md
- /home/ogre/spot-stack/watch/inventory/worker-05.json
- /home/ogre/spot-stack/watch/standby-registration/WORKER05-STANDBY-DRAFT-20260505-002114.json

Worker-05 command surface:
- watch/spot-client.sh worker05-status
- watch/spot-client.sh worker05-verify
- watch/spot-client.sh worker05-routing-guard
- watch/spot-client.sh worker05-ask <prompt>
- watch/spot-client.sh worker05-standby-draft
- watch/spot-client.sh worker05-standby-drafts [count]
- watch/spot-client.sh show-worker05-standby-draft <id-or-file>
- watch/spot-client.sh worker05-standby-draft-verify <id-or-file>

Worker-05 must remain out of production routing until a future reviewed routing slice adds router support for:
- enabled
- eligible
- routing_enabled
- manual_only

---

## ACTIVE PRODUCTION ROUTING

Production primaries remain:

```text
general -> spot-worker-01
utility -> spot-worker-02
coding  -> spot-worker-03
heavy   -> spot-worker-04
```

Worker-05 is not in:
- active role_priority
- active workers map
- warm_model_policy targets
- burst_policy

---

## WORKER-04 GPU UPGRADE PLAN

Worker-04 remains the heavy primary.
Its new GPU is expected next.

After worker-04 new GPU is physically installed, do not change routing ownership. Keep:

```text
heavy -> spot-worker-04
worker-05 -> heavy-secondary standby
```

Worker-04 post-GPU validation path:

1. Boot worker-04 after GPU install.
2. Verify PCI detection:
   - lspci | egrep -i 'nvidia|vga|3d|display'
3. Verify NVIDIA driver:
   - nvidia-smi
   - nvidia-smi --query-gpu=index,name,memory.total,memory.free,temperature.gpu,power.draw,driver_version --format=csv,noheader,nounits
4. Verify nvidia-persistenced active.
5. Verify Ollama active.
6. Run local Ollama GPU smoke.
7. Verify remote health/API from spot-core.
8. Run spot validate.
9. Update docs and checkpoint.

Do not promote worker-05 to automatic routing just because worker-04 hardware changes.

---

## NEXT ENGINEERING LANE

Next active Phase 2 work:

PHASE 2.32 — TASK REVIEW / LIFECYCLE CHECKPOINT

Completed since last state checkpoint:
- Phase 2.31 added non-mutating task artifact schema and utility.
- Phase 2.31 exposed task create/list/show/verify/summary through `watch/spot-ops.sh`.
- Task artifact journaling linkage validated successfully.
- Task artifacts remain proposal-only and non-mutating by policy.
- Latest validation passed at `2026-05-08T00:01:24Z` with `pass=19 warn=0 fail=0`.

Recommended scope:
- add explicit task review lifecycle
- add reviewed/rejected state handling
- preserve proposal-only behavior
- preserve immutable journaling
- preserve Spot Core apply authority
- no service restarts
- no config writes
- no network mutation
- no live backup creation
- no live backup binding
- no executor dispatch
- no autonomous apply

Do not enable mutation plugins until a future reviewed slice explicitly implements:
- backup binding
- precheck validation
- postcheck validation
- rollback contract
- append-only action logs
- explicit plugin allowlist
- supervised apply review

---

## FLEET SNAPSHOT

worker-01 = general primary
worker-02 = utility primary, healthy but latency warning-level
worker-03 = coding primary
worker-04 = heavy primary, new GPU pending
worker-05 = heavy-secondary standby, manual-only, not production-routed

Latest observed checkpoint trend:
- worker-01 healthy and fast
- worker-02 healthy but slow, p50 around 10s in recent checkpoints
- worker-03 healthy and fast
- worker-04 healthy and fast
- worker-05 validated standby / manual ask works

Hardware lane update:
- Worker-04 received the new Quadro P6000 24GB GPU, validated successfully, and remains the heavy primary.
- Worker-05 memory was upgraded from 16GB to 32GB, but worker-05 remains standby/manual-only unless explicitly promoted in a later reviewed slice.
- Worker-02 is the Dell Precision chassis with PSU/GPU power constraints: only 2x 6-pin GPU power is available.
- The planned swap of worker-04's former 16GB GPU into worker-02, replacing the 6GB GPU, is blocked by worker-02 power constraints.
- Worker-02 remains on the existing 6GB + 8GB GPU layout for now unless replaced.
- Future expansion option: add worker-06 with the 16GB + 8GB GPUs, or replace worker-02 with a chassis/PSU that can support the intended GPU layout.

Hardware metadata checkpoint:
- Worker-04 received the Quadro P6000 24GB GPU, validated successfully, and remains the heavy primary.
- Worker-04 routing/config label should be Quadro P6000 24GB, replacing the stale TITAN Xp 12GB label.
- Worker-05 RAM was upgraded from 16GB to 32GB, but worker-05 remains standby/manual-only unless explicitly promoted in a later reviewed slice.
- Worker-02 is the Dell Precision chassis with Quadro M4000 8GB + GTX 1060 6GB.
- Worker-02 PSU/GPU power constraints block the planned installation of worker-04's former 16GB GPU; worker-02 remains on the existing 8GB + 6GB layout unless replaced.
- Worker-02 numeric CUDA indexing is unreliable for pinning; use GPU UUIDs if pinning is needed.
## Starfleet Fleet Layout Update — 7 Worker Target

Current target layout after hardware shuffle:

| Worker | Target role | Target hardware / notes |
|---|---|---|
| spot-worker-01 | General Prime | EPYC 4245P, 32GB RAM, RTX 3060 12GB. Keep as general primary. |
| spot-worker-02 | Aux / Embeddings / Lab | Dell Precision T3610, Xeon E5-1620 v2, Quadro M4000 8GB + GTX 1060 6GB. Demote from primary utility after worker-06 validates. Keep for embeddings, low-risk services, lab, and fallback. |
| spot-worker-03 | Coding Prime | Ryzen 7 2700X, 32GB RAM, GTX 1070 8GB + RTX 3060 12GB. Keep as coding primary. |
| spot-worker-04 | Heavy Prime | i7-13700KF, 64GB RAM, Quadro P6000 24GB. Primary heavy / premium inference lane. |
| spot-worker-05 | Spot UI Visual / Render Node | Receives 12GB GPU after P6000 transfer. Use for Spot UI 3D, visual rendering, map/dashboard graphics, experimental UI workloads. Not primary inference. |
| spot-worker-06 | Utility Prime Candidate | New Z97/i5-4570 box, 32GB RAM, currently 8GB + 4GB GPU for initial validation. Future likely 8GB + Quadro M4000 8GB if worker-02 is demoted and transplant is validated. |
| spot-worker-07 | Heavy Secondary Candidate | i9-9900K / Z390 class, 64GB RAM planned, receives Quadro P6000 24GB from worker-05. Heavy secondary / overflow premium lane after validation. |

Routing intent after validation:
- General owner remains spot-worker-01.
- Coding owner remains spot-worker-03.
- Heavy owner remains spot-worker-04 initially.
- Heavy secondary adds spot-worker-07 after validation.
- Utility owner migrates from spot-worker-02 to spot-worker-06 only after worker-06 passes live validation.
- spot-worker-02 becomes aux/embeddings/lab, not dead/retired.
- spot-worker-05 becomes visual/render support for Spot UI, not standby-only.

Hardware guardrails:
- Do not cannibalize worker-02 until worker-06 passes Linux, NVIDIA, Ollama, thermal, PSU, and uptime validation.
- Do not promote worker-07 until P6000 fitment, power, thermals, driver, Ollama, and heavy smoke tests pass.
- Do not change Spot routing ownership until the new node has clean validation artifacts.
- Treat existing worker-04 P6000 state as current truth; older worker-04 TITAN Xp references are stale.
- Numeric CUDA indexing is unreliable on worker-02; use GPU UUID if pinning is required.

## New Worker Onboarding Checklist — worker-06 / worker-07

Before routing changes, each new worker must pass:

1. OS / identity
   - Ubuntu Server installed
   - hostname set correctly
   - static DHCP / DNS reservation planned
   - SSH key access from spot-core working

2. Hardware visibility
   - CPU confirmed with `lscpu`
   - RAM confirmed with `free -h`
   - GPUs confirmed with `lspci` and `nvidia-smi`
   - storage confirmed with `lsblk`
   - PSU/cooling inspected physically

3. NVIDIA / Ollama
   - NVIDIA driver loaded
   - `nvidia-smi` clean
   - `nvidia-persistenced` active
   - Ollama installed and active
   - Ollama sees intended GPU(s)
   - no numeric CUDA pinning unless proven safe; prefer UUID pinning

4. Network / mounts
   - reachable from spot-core
   - `curl http://<worker>:11434/api/tags` works from spot-core
   - `/mnt/collective` mounted if required
   - DNS/search domain behavior checked

5. Smoke tests
   - local Ollama generate works
   - remote Ollama generate from spot-core works
   - GPU memory and thermals stay sane
   - no zombie runners
   - reboot returns cleanly

6. Spot integration
   - add worker to cluster config only after validation
   - keep route ownership unchanged until validation passes
   - run `watch/spot-ops.sh validate`
   - confirm routing audit labels and role ownership
   - commit config/docs before activation

Worker-specific notes:
- worker-06 starts as utility prime candidate. Do not replace worker-02 as utility owner until worker-06 proves stable.
- worker-07 starts as heavy secondary candidate. Do not add as heavy route until P6000 validation passes.

## Phase 2 Closeout Direction

Current Phase 2 status:
- Phase 2.1 through Phase 2.31 are complete and non-mutating.
- Executor contracts, immutable journaling, and non-mutating task artifacts are operational.
- Live backup creation remains forbidden until a separate reviewed design slice is completed.
- Current next autonomy lane is Phase 2.32 task review/lifecycle design.
- Before deeper autonomy work, align fleet hardware documentation and onboard worker-06 / worker-07 safely.

Immediate priority order:
1. Update fleet support docs for 7-worker target layout.
2. Validate worker-06 as utility prime candidate.
3. Validate worker-07 as heavy secondary candidate.
4. Update cluster config only after validation.
5. Run HANDOFF-SPOT-INTEGRATION.md.
6. Run HANDOFF-CODEX-INTEGRATION.md.
7. Then resume Spot UI / visual lane using worker-05 as visual/render node.

Phase 2 must not proceed to live backup creation implementation until:
- design review is committed,
- backup target allowlist is defined,
- immutable backup artifact behavior is verified,
- restore/rollback proof exists,
- operator approval flow is explicit.
---

## HISTORICAL CHECKPOINT ARCHIVE — 2026-05-07

Status:
- PASS
- validated
- committed
- non-mutating

Completed:
- Registered `spot-worker-03` as the first capability-managed Codex executor.
- Added capability manifest:
  - `watch/capabilities/spot-worker-03.json`
- Added capability registry operator tool:
  - `watch/spot-capabilities.sh`
- Extended operator surface:
  - `watch/spot-ops.sh capabilities`
  - `watch/spot-ops.sh capability <worker>`
  - `watch/spot-ops.sh find-capability <name>`

Current executor posture:
- `codex_enabled = true`
- `mode = worktree_patch_only`
- `live_write_allowed = false`
- `service_restart_allowed = false`
- `requires_spot_core_apply = true`

Current Codex integration state:
- `spot-worker-03` hosts isolated Codex worktree execution environment.
- Per-task git worktree creation operational.
- Artifact/log generation operational.
- Patch-only workflow operational.
- Bubblewrap namespace sandbox currently degraded on worker-03.
- Temporary operation currently uses bypassed Codex sandbox inside isolated worktrees only.
- Live runtime mutation remains forbidden.

Validation:
- `watch/spot-ops.sh capabilities` PASS
- `watch/spot-ops.sh capability spot-worker-03` PASS
- `watch/spot-ops.sh find-capability codex_runner` PASS
- `watch/spot-ops.sh validate` PASS
- Validation timestamp:
  - `2026-05-07T14:55:23Z`
  - `pass=19 warn=0 fail=0`

Design direction:
- Codex is treated as an executor/reasoning layer.
- spot-core remains the authoritative policy, backup, validation, and rollback layer.
- Future autonomy must preserve:
  - no backup, no change
  - append-only audit
  - rollback-first design
  - restricted network mutation
  - explicit execution policy

Next planned lane at archive checkpoint time:
1. Validation-gated live apply workflow
2. Controlled task review lifecycle
3. Capability-aware scheduling refinement
4. Controlled autonomous remediation review
