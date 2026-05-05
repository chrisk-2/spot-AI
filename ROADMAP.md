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

Status: ACTIVE — NON-MUTATING CONTROL STACK COMPLETE THROUGH PHASE 2.13.

Current active next slice:

## Phase 2.14 — Executor dry-run preflight contract

Status: NEXT.

Allowed scope:
- define executor preflight contract artifact
- require plugin request verification
- require plugin registry verification
- require action policy verification
- require dry-run only
- require all execution/mutation flags false
- produce preflight artifact only
- no service restarts
- no config writes
- no network mutation
- no backup binding for mutation yet

Phase 2 remains a non-mutating control-plane build until a later reviewed slice explicitly enables narrow execution.

Current checkpoint before Phase 2.14:
- `60daec0 worker05: add guarded standby registration draft`

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

PHASE 2.14 — Executor dry-run preflight contract.

Do not enable mutation plugins until a future reviewed slice implements backup binding, validation, rollback, append-only logs, and explicit plugin allowlist enforcement.

Do not enable worker-05 automatic routing until a future reviewed routing slice implements enabled/eligible/routing_enabled/manual_only enforcement.
