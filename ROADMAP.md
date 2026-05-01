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

Status: **complete for current scope**.

Spot Core foundation is locked. Operator workflows and MCP/operator command surfaces are functionally live.

Completed:

- standardized operator entry points through `spot-ops.sh`
- MCP-safe operator commands for `status`, `validate`, `routing`, `audit`, `latency`, `quarantine_state`, and `readiness`
- live `/operator/readiness` endpoint
- read-only command risk classification validated as low risk
- fleet validation currently returns PASS
- routing ownership remains strict:
  - general -> spot-worker-01
  - utility -> spot-worker-02
  - coding -> spot-worker-03
  - heavy -> spot-worker-04
- operator quick-health shows workers and endpoints healthy

Remaining Phase 1 debt:

- worker-02 utility latency remains warning-level in readiness
- worker-02 and worker-03 multi-GPU topology still needs true GPU-pinned Ollama service separation before lane labels are fully authoritative

Goal met:

Spot is stable enough to act as an operator-ready engineering/control assistant.

---

# PHASE 1.5 — SPOT ASSISTANT CLIENT SURFACE

Status: **mostly complete; active maturation continues**.

Spot now has a practical assistant/client layer usable from the terminal.

Completed/live:

- `spot ask` read-only/routed prompt client
- live telemetry shortcuts for fleet status, routing audit, and latency questions
- automatic role selection for common task types
- route metadata visibility
- durable memory context injection
- `spot propose` proposal-first engineering/planning client
- canonical path and validation-command guardrails in proposal mode
- proposal guardrail scanner for forbidden invented paths/services
- proposal persistence:
  - `spot propose --save`
  - `spot proposals`
  - `spot show-proposal`
- proposal lifecycle:
  - `spot approve`
  - `spot reject`
  - `spot proposal-status`

Goal met:

Spot can now be used as a terminal engineering assistant with proposal memory and approval gates.

Remaining maturation:

- continue strengthening proposal quality and historical awareness
- keep all mutation routed through Spot Core backup-first enforcement

---

# PHASE 1.6 — PERSISTENT MEMORY FOUNDATION

Status: **base layer live**.

Completed/live:

- `spot remember`
- `spot memory`
- `spot recall`
- Unimatrix-backed JSONL memory backend
- memory injection into `spot ask`
- memory injection into `spot propose`
- proposal/apply lifecycle durable memory logging

Design rule:

Memory informs context. Memory is not authorization.

Remaining memory work:

- correction/edit/audit workflow for bad memory entries
- better deduplication and indexing
- eventual UI display/search
- long-term vector/index layer after append-only JSONL proves stable

---

# PHASE 1.7 — SUPERVISED APPLY-PLAN ENGINE

Status: **current active lane**.

This is the bridge between proposal-only planning and future controlled mutation.

Completed/live runtime layer:

- `spot generate-apply-plan <approved-proposal>`
- `spot apply-plans [count]`
- `spot show-apply-plan <apply-plan>`
- `spot apply-plan-status <apply-plan>`
- `spot apply-plan-check <apply-plan>`
- `spot apply-plan-verify <apply-plan>`
- `spot approve-apply-plan <apply-plan>`
- `spot reject-apply-plan <apply-plan>`
- `spot generate-patch` retained as legacy alias to supervised apply-plan generation

Current semantics:

- approved proposal -> specific apply-plan artifact
- apply-plan lifecycle states: pending review / review approved / review rejected
- backup requirements listed before any mutation
- validation and rollback requirements listed before any mutation
- policy classification tied to Spot Autonomy Policy
- blocked generation for unapproved/rejected proposals
- apply-plan verification gates exist
- no direct config mutation unless routed through future Spot Core enforcement wrappers
- all current apply-plan artifacts remain `mutation_allowed: false`

Non-goals for this phase:

- no unrestricted auto-apply
- no bypassing backup-first enforcement
- no high-risk network/firewall/DNS/DHCP/VLAN/routing mutation outside narrow approved endpoints

Remaining Phase 1.7 exit work:

- backup binding/checkpoint reference design for future execution
- controlled handoff from `review_approved` artifact to future Spot Core execution wrapper
- final apply artifact semantics/documentation tightening
- checkpoint after meaningful slices only

Exit criteria:

- approved proposals produce specific, reviewable apply-plan artifacts
- artifact lifecycle states are inspectable and verifiable
- backup/validation/rollback are explicit in every artifact
- reviewed artifacts can be verified without mutation
- Spot Core and validator remain green afterward

---

# PHASE 2 — BUILD SPOT CONTROLLED AUTONOMY

Status: **not active yet**.

Important note:

The monitoring/heartbeat substrate already exists and is active:

- `fleet-watch.timer`
- `fleet-remediate.timer`
- `spot-monitor-alert-state.timer`
- `spot-monitor-snapshot.timer`

The monitor snapshot layer has been repaired and is producing fresh summaries/snapshots again.

Therefore Phase 2 is not “build monitoring from zero.”

Phase 2 is:

- formal incident engine from existing watcher alerts
- remediation class policy
- safe self-fix logic inside approved boundaries
- autonomous action logs
- controlled execution wrapper integration
- rollback verification
- detect -> analyze -> classify -> backup -> plan -> verify -> execute -> test/rollback chain

No backup, no change.

Goal:

Spot becomes an operations brain, not only a manual router.

---

# PHASE 3 — SPOT AS BUILD ASSISTANT

Status: **future**.

Tie together:

- Spot Core
- Spot UI
- Codex
- worker-03 engineering lane
- git checkpoint workflow
- proposal/apply engineering loop
- persistent memory

Goal:

Spot helps inspect, patch, validate, and build future layers under supervision.

---

# PHASE 4 — STARFLEET OS CORE

Status: **future**.

Construct the integrated Starfleet command environment.

Planned direction:

- installable/local app surface
- web/PWA console first
- later desktop wrapper if useful
- LCARS-style operator UI when backend workflows are stable
- Spot as the control brain underneath Starfleet OS

---

# PHASE 5 — STARFLEET HA SECURITY SYSTEM

Status: **future**.

Unified home/office security collective on top of Starfleet OS.

---

# PHASE 6 — LONG RANGE EXPANSION

Status: **future**.

Expansion only after core maturity.

---

# CURRENT ACTIVE PHASE

Current active lane:

**PHASE 1.7 — SUPERVISED APPLY-PLAN ENGINE**

The project is past Milestone B operator standardization, past the first usable assistant-client layer, past the persistent memory foundation, and is now in controlled execution preparation.

Immediate next objective:

Finish the final supervised apply-plan semantics and execution handoff design without enabling unrestricted mutation.

Keep these constraints active:

- Spot Core holds the keys
- clients propose and review
- approved artifacts can be generated and verified
- actual mutation must remain backup-first, verified, logged, and routed through Spot Core enforcement
