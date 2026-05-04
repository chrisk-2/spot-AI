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

Completed:
- approved proposal -> reviewable apply-plan generation
- apply-plan lifecycle review/approve/reject/check/verify surfaces
- execution handoff generation and verification
- supervised dry-run execution wrapper
- execution-run artifacts and verify routines
- backup-bound prechange artifact creation
- SHA256 backup integrity verification
- dry-run/no-mutation run contract
- no-backup-no-change enforcement at wrapper level

Carry-forward constraints:
- no unrestricted auto-apply
- no bypassing backup-first enforcement
- no autonomous mutation
- no high-risk network/firewall/DNS/DHCP/VLAN/routing mutation outside future explicitly approved endpoints

---

# PHASE 2 — BUILD SPOT CONTROLLED AUTONOMY

Status: ACTIVE — NON-MUTATING CONTROL STACK COMPLETE THROUGH PHASE 2.9.

Phase 2 is building the control, policy, audit, and lifecycle rails for controlled autonomy before enabling any mutation.

Current checkpoint:
- `77de4b6 phase29: add action handoff review lifecycle and audit`

Completed slices:

## Phase 2.1 — Execution-run lifecycle
Status: complete.

## Phase 2.2 — Execution-run read-only visibility
Status: complete.

## Phase 2.3 — Action policy manifest
Status: complete.

Created:
- `watch/policy/action-policy.json`

## Phase 2.4 — Action policy verifier
Status: complete.

Created:
- `spot-client.sh action-policy-verify`

## Phase 2.5 — Non-executing action request artifacts
Status: complete.

Created:
- `watch/action-requests/ACTION-*.json`

## Phase 2.6 — Action request lifecycle
Status: complete.

States:
- draft_non_executing
- review_approved_non_executing
- review_rejected
- closed_no_execution

## Phase 2.7 — Action request audit/summary
Status: complete.

## Phase 2.8 — Non-executing action handoff bridge
Status: complete.

Created:
- `watch/action-handoffs/ACTION-HANDOFF-*.json`

## Phase 2.9 — Action handoff lifecycle/audit
Status: complete.

States:
- prepared_non_executing
- review_approved_non_executing
- review_rejected
- closed_no_execution

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
```

Current hard limits:
- mutation_plugins_enabled=false
- execution_allowed=false
- mutation_allowed=false
- mutation_performed=false
- backup_artifact=pending on non-executing action handoffs
- next_allowed_action=manual_review_only
- network_change restricted_disabled
- freeform_shell_mutation forbidden
- backup_delete_or_overwrite forbidden

---

# PHASE 2.10 — CONTROLLED EXECUTOR SKELETON / PLUGIN REGISTRY MANIFEST

Status: NEXT CANDIDATE.

Allowed scope:
- plugin registry manifest
- all plugins disabled by default
- registry display command
- registry verifier
- no plugin execution
- no service restart
- no config write
- no backup binding for mutation
- no network/firewall/DNS/DHCP/VLAN/routing mutation

Required safety posture:
- registry verifier must fail if any plugin is enabled before reviewed implementation
- plugin classes must map to action policy classes
- all execution must remain blocked

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

Build Phase 2.10 as a non-executing plugin registry manifest and verifier.

Do not enable mutation plugins until a future reviewed slice implements backup binding, validation, rollback, append-only logs, and explicit plugin allowlist enforcement.
