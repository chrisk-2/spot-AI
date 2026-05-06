# STARFLEET FORWARD ROADMAP

## PURPOSE

This file defines the phased forward construction path for Starfleet / Spot Core.

Runtime truth and exact current status live in:

- `/home/ogre/spot-stack/spot-core/STATE.md`

Locked workflow and policy rules live in:

- `/home/ogre/spot-stack/HANDOFF.md`
- `/home/ogre/spot-stack/Spot_Autonomy_Policy`
- `/home/ogre/spot-stack/HANDOFF-CODEX-INTEGRATION.md`
- `/home/ogre/spot-stack/HANDOFF-SPOT-INTEGRATION.md`

---

# PHASE 1 — SPOT OPERATOR READY

Status: complete for current scope.

---

# PHASE 1.5 — SPOT ASSISTANT CLIENT SURFACE

Status: complete for current supervised scope.

---

# PHASE 1.6 — PERSISTENT MEMORY FOUNDATION

Status: base layer live.

---

# PHASE 1.7 — SUPERVISED APPLY-PLAN ENGINE

Status: COMPLETE / BASELINE LOCKED.

Phase 1.7 bridged proposal-only planning into supervised execution preparation without enabling mutation.

Canonical proof:
- commit `4e17214`
- verified run `RUN-HANDOFF-APPLY-phase17-lifecycle-test-041538-20260504-030310`

Carry-forward constraints:
- no unrestricted auto-apply
- no bypassing backup-first enforcement
- no autonomous mutation
- no high-risk network/firewall/DNS/DHCP/VLAN/routing mutation outside future explicitly approved endpoints

---

# PHASE 2 — BUILD SPOT CONTROLLED AUTONOMY

Status: ACTIVE — NON-MUTATING CONTROL STACK COMPLETE THROUGH PHASE 2.28.

Current active next slice:

## Phase 2.29 — Readiness gate decision checkpoint

Status: NEXT.

Allowed scope:
- define a go/no-go readiness checkpoint for future live backup work
- aggregate proof from executor preflight, backup-binding contract, manifest contract, and manifest dry-run lanes
- verify all known summaries are clean
- verify all failure-path harnesses pass
- produce checkpoint artifact only
- preserve dry-run only behavior
- require all execution/mutation flags false
- no service restarts
- no config writes
- no network mutation
- no live backup creation
- no live backup binding
- no real checksum generation over live files
- no executor dispatch

Phase 2 remains a non-mutating control-plane build until a later reviewed slice explicitly enables narrow execution.

Current checkpoint before Phase 2.29:
- Phase 2.26 backup artifact manifest dry-run simulator implemented
- Phase 2.27 backup artifact manifest dry-run operator surface implemented
- Phase 2.28 backup artifact manifest dry-run summary/failure validation implemented and passed
- latest checkpoint: `11e9c38 phase2: add backup artifact manifest dry-run summary and failure validation`

Completed Phase 2 slices:

## Phase 2.1 — Execution-run lifecycle
Status: complete.

## Phase 2.2 — Execution-run read-only visibility
Status: complete.

## Phase 2.3 — Action policy manifest
Status: complete.

## Phase 2.4 — Action policy verifier
Status: complete.

## Phase 2.5 — Non-executing action request artifacts
Status: complete.

## Phase 2.6 — Action request lifecycle
Status: complete.

## Phase 2.7 — Action request audit/summary
Status: complete.

## Phase 2.8 — Non-executing action handoff bridge
Status: complete.

## Phase 2.9 — Action handoff lifecycle/audit
Status: complete.

## Phase 2.10 — Disabled plugin registry manifest
Status: complete.

## Phase 2.11 — Plugin registry audit/summary
Status: complete.

## Phase 2.12 — Non-executing plugin request artifacts
Status: complete.

## Phase 2.13 — Plugin request lifecycle/audit
Status: complete.

## Phase 2.14 — Executor dry-run preflight contract
Status: complete.

Phase 2.14 added `watch/spot-executor-preflight.sh` and the `watch/executor-preflights/` artifact lane. It verifies the plugin request, plugin registry, and action policy before producing a dry-run-only executor preflight artifact. Successful Phase 2.14 preflight artifacts intentionally report `ok=true` and `blocked=true` while keeping execution, mutation, plugin dispatch, service restart, config write, network mutation, and backup binding disabled.

## Phase 2.15 — Executor preflight lifecycle/operator surface
Status: complete.

Phase 2.15 exposed executor preflight create/list/show/verify through `watch/spot-ops.sh`, added operator-surface proof, and added executor preflight audit summary generation. The summary confirms known preflight artifacts are blocked and non-mutating.

## Phase 2.16 — Executor preflight failure-path validation
Status: complete.

Phase 2.16 added `watch/spot-executor-preflight-failure-test.sh` and negative fixtures proving unsafe plugin request variants are rejected before preflight artifact creation. Rejected cases include execution enabled, mutation enabled, mutation performed, backup already bound, unknown plugin, bad schema, and non-closed request status.

## Phase 2.18 — Backup-binding contract design
Status: complete.

Phase 2.18 added `watch/spot-backup-binding-contract.sh` and the `watch/backup-binding-contracts/` artifact lane. It defines future backup-binding contract shape only. Generated contracts are design-only, blocked, non-mutating, and explicitly do not create or bind backups.

## Phase 2.19 — Backup-binding contract operator surface
Status: complete.

Phase 2.19 exposed backup-binding contract create-design/list/show/verify through `watch/spot-ops.sh` and added an operator-surface proof artifact. All backup creation, live binding, execution, mutation, and dispatch gates remain false.

## Phase 2.20 — Backup-binding contract summary/failure validation
Status: complete.

Phase 2.20 added backup-binding contract summary generation and `watch/spot-backup-binding-contract-failure-test.sh`. The failure harness rejected unsafe contract variants including live mode, bound status, backup creation allowed, backup binding active, execution/mutation/dispatch enabled, backup delete/overwrite allowed, bad rollback authority, and result not blocked.

## Phase 2.22 — Backup artifact manifest contract design
Status: complete.

Phase 2.22 added `watch/spot-backup-artifact-manifest-contract.sh` and the `watch/backup-artifact-manifest-contracts/` artifact lane. It defines the future backup artifact manifest contract only. Generated contracts are design-only, blocked, non-mutating, and explicitly do not create manifests, checksums, backups, or backup bindings.

## Phase 2.23 — Backup artifact manifest operator surface
Status: complete.

Phase 2.23 exposed backup artifact manifest contract create-design/list/show/verify through `watch/spot-ops.sh` and added an operator-surface proof artifact. All manifest creation, checksum generation, backup creation, live binding, execution, mutation, and dispatch gates remain false.

## Phase 2.24 — Backup artifact manifest summary/failure validation
Status: complete.

Phase 2.24 added backup artifact manifest contract summary generation and `watch/spot-backup-artifact-manifest-contract-failure-test.sh`. The failure harness rejected unsafe manifest contract variants including live mode, created status, manifest/checksum filename drift, checksum algorithm drift, backup artifact creation, checksum generation, backup creation allowed, backup binding active, execution/mutation/dispatch enabled, and result not blocked.

## Phase 2.26 — Backup artifact manifest implementation dry-run simulator
Status: complete.

Phase 2.26 added `watch/spot-backup-artifact-manifest-dry-run.sh` and the `watch/backup-artifact-manifest-dry-runs/` artifact lane. It simulates future backup artifact manifest generation without reading live source files, hashing live source files, creating manifests, creating backups, binding backups, or authorizing execution.

## Phase 2.27 — Backup artifact manifest dry-run operator surface
Status: complete.

Phase 2.27 exposed backup artifact manifest dry-run create/list/show/verify through `watch/spot-ops.sh` and added an operator-surface proof artifact. All live file read, live hash, backup manifest creation, backup artifact creation, checksum generation, backup creation, backup binding, execution, mutation, and dispatch gates remain false.

## Phase 2.28 — Backup artifact manifest dry-run summary/failure validation
Status: complete.

Phase 2.28 added backup artifact manifest dry-run summary generation and `watch/spot-backup-artifact-manifest-dry-run-failure-test.sh`. The failure harness rejected unsafe dry-run variants including live mode, live source file reads, live source file hashing, manifest creation, backup artifact creation, checksum generation, backup creation allowed, backup binding active, backup verified, execution/mutation/dispatch enabled, service restart/config write/network mutation enabled, and result not blocked.

Current control chain:

```text
policy manifest
-> policy verifier
-> action request
-> action request verifier
-> action request lifecycle
-> action request audit/summary
-> action handoff candidate
-> action handoff verifier
-> action handoff lifecycle
-> action handoff audit/summary
-> plugin registry
-> plugin registry verifier/audit
-> plugin request
-> plugin request verifier/lifecycle/audit
-> executor dry-run preflight contract
-> executor preflight operator surface/audit summary
-> executor preflight failure-path validation
-> backup-binding contract design
-> backup-binding contract operator surface/summary
-> backup-binding contract failure-path validation
-> backup artifact manifest contract design
-> backup artifact manifest contract operator surface/summary
-> backup artifact manifest contract failure-path validation
-> backup artifact manifest dry-run simulator
-> backup artifact manifest dry-run operator surface/summary
-> backup artifact manifest dry-run failure-path validation
```

Current hard limits:
- mutation_plugins_enabled=false
- plugin_execution_enabled=false
- plugin_execution_allowed=false
- execution_allowed=false
- mutation_allowed=false
- mutation_performed=false
- network_change restricted_disabled/forbidden depending layer
- freeform_shell_mutation forbidden
- backup_delete_or_overwrite forbidden

---

# WORKER-05 STANDBY INTEGRATION TRACK

Status: complete for safe standby/manual scope.

Latest checkpoint:
- `60daec0 worker05: add guarded standby registration draft`

worker-05 current mode:

```text
role = heavy-secondary
standby = true
burst_candidate = true
fallback_candidate = true
routing_enabled = false
primary = false
production_role = none
manual ask = allowed through worker05-ask only
```

Completed worker-05 slices:
- GPU installed and validated
- NVIDIA 535.288.01 active
- Quadro P6000 with 23040 MiB VRAM
- Ollama GPU smoke passed
- remote Ollama API passed
- remote GPU inference confirmed
- passwordless SSH from core passed
- passwordless sudo from core passed
- health endpoint status corrected to gpu_validated_pre_routing
- commissioning runbook added
- non-routing inventory record added
- standby health verifier added
- standby routing guard added
- manual standby ask command added
- guarded standby registration draft added

Worker-05 remains out of production routing.

Before any automatic worker-05 routing:
- add router enforcement for enabled/eligible/routing_enabled/manual_only
- add validator guard preventing worker-05 from becoming primary
- use a reviewed apply slice
- prove worker-05 only appears during explicit burst/fallback tests

---

# WORKER-04 GPU UPGRADE TRACK

Status: pending hardware.

worker-04 remains heavy primary before and after the GPU upgrade unless a separate reviewed routing change says otherwise.

After worker-04 new GPU is installed:

1. Verify PCI detection:
   - `lspci | egrep -i 'nvidia|vga|3d|display'`
2. Verify NVIDIA driver:
   - `nvidia-smi`
   - `nvidia-smi --query-gpu=index,name,memory.total,memory.free,temperature.gpu,power.draw,driver_version --format=csv,noheader,nounits`
3. Verify nvidia-persistenced.
4. Verify Ollama.
5. Run local Ollama GPU smoke.
6. Validate remote health and remote Ollama from spot-core.
7. Run `spot validate`.
8. Update support docs and checkpoint.

Expected post-upgrade routing posture:

```text
heavy -> spot-worker-04
worker-05 -> heavy-secondary standby/manual-only
```

---

# PHASE 3 — SPOT AS BUILD ASSISTANT

Status: future.

---

# PHASE 4 — STARFLEET OS CORE

Status: future.

---

# PHASE 5 — STARFLEET HA SECURITY SYSTEM

Status: future.

---

# PHASE 6 — LONG RANGE EXPANSION

Status: future.

---

# CURRENT ACTIVE PHASE

Current active lane:

PHASE 2 — BUILD SPOT CONTROLLED AUTONOMY

Immediate next objective:

PHASE 2.29 — Readiness gate decision checkpoint.

Do not enable mutation plugins until a future reviewed slice implements backup binding, validation, rollback, append-only logs, and explicit plugin allowlist enforcement.

Do not enable worker-05 automatic routing until a future reviewed routing slice implements enabled/eligible/routing_enabled/manual_only enforcement.

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
- Phase 2.1 through Phase 2.29 are complete and non-mutating.
- Phase 2.29 readiness gate returned GO_FOR_DESIGN_REVIEW_ONLY.
- Live backup creation remains forbidden until a separate reviewed design slice is completed.
- Current next autonomy lane is design-only: live backup creation design review.
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
