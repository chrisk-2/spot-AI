# STARFLEET FORWARD ROADMAP

## PURPOSE

This file defines the phased forward construction path after the Spot rescue/hardening phase.

This is the canonical build lane for the project.

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

This phase successfully bridged proposal-only planning into supervised execution preparation without enabling autonomous mutation.

Completed/live:

- approved proposal -> reviewable apply-plan generation
- apply-plan lifecycle review/approve/reject/check/verify surfaces
- execution handoff generation and verification
- supervised dry-run execution wrapper (`watch/spot-apply.sh`)
- execution run artifacts and verify routines
- backup-bound prechange artifact creation
- SHA256 integrity verification of recorded backups
- run contract proving dry-run/no-mutation semantics
- no-backup-no-change enforcement at wrapper level
- all execution remains `execution_allowed: false`
- all mutation remains `mutation_allowed: false`

Canonical proof:
- commit `4e17214`
- verified run `RUN-HANDOFF-APPLY-phase17-lifecycle-test-041538-20260504-030310`

Exit criteria met:
- approved proposals produce specific reviewable apply artifacts
- artifact lifecycle states are inspectable and verifiable
- backup/validation/rollback are explicit in every artifact
- reviewed artifacts can be verified through supervised wrapper without mutation
- Spot Core and validator remain green afterward

Locked carry-forward constraints:
- no unrestricted auto-apply
- no bypassing backup-first enforcement
- no autonomous mutation
- no high-risk network/firewall/DNS/DHCP/VLAN/routing mutation outside narrow approved endpoints

---

# PHASE 2 — BUILD SPOT CONTROLLED AUTONOMY

Status: NEXT ACTIVE LANE.

Phase 2 does not begin with raw autonomous mutation. It begins from the proven Phase 1.7 dry-run shell.

Phase 2 immediate construction goals:

- formal incident/execution state machine from existing watcher alerts
- explicit remediation class policy mapping
- controlled execution wrapper evolution from dry-run -> supervised mutation stubs
- mutation plugin dispatch framework still default-disabled
- rollback verification contracts
- detect -> analyze -> classify -> backup -> plan -> verify -> execute -> validate chain
- full audit logging of every supervised action

Important:
actual mutation remains disabled until Phase 2 policy slices are explicitly implemented and reviewed.

No backup, no change remains absolute.

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

The project is past operator stabilization, past the assistant-client layer, past persistent memory, and past supervised dry-run execution proof.

Immediate next objective:

Build the first policy-bound controlled execution state machine on top of the Phase 1.7 backup-bound dry-run wrapper without enabling free autonomous mutation.

Keep these constraints active:

- Spot Core holds the keys
- clients propose and review
- approved artifacts can be generated and verified
- every execution remains backup-first, verified, logged, and policy-bound
- mutation plugins remain disabled until explicitly enabled by future reviewed slices
