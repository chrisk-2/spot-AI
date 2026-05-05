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
