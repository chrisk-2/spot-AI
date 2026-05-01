# STARFLEET FORWARD ROADMAP

## PURPOSE

This file defines the phased forward construction path after the Spot rescue/hardening phase.

This is the canonical build lane.

---

# PHASE 1 — SPOT OPERATOR READY

Spot Core foundation is locked. Operator workflows and MCP operator command surface are now functionally live.

Completed/mostly complete:
- standardized MCP operator entry points (`status`, `validate`, `routing`, `audit`, `latency`, `quarantine_state`, `readiness`)
- live `/operator/readiness` endpoint
- validated operator command risk gating for read-only workflows
- validated fleet PASS state with only worker-02 latency warning remaining

Remaining Phase 1 debt:
- worker-02 utility latency remains warning-level
- multi-GPU worker-02 and worker-03 are not yet truly GPU-pinned per Ollama service
- terminal/client ergonomics still missing

Goal:
Spot = stable operator-ready engineering/control assistant.

---

# PHASE 1.5 — SPOT ASSISTANT CLIENT SURFACE

Build the practical assistant layer that makes Spot usable like a daily engineering copilot.

Build:
- `spot ask` read-only routed prompt client
- `spot propose` proposal-first engineering/planning client
- clean stdout/json modes
- role override flags (`general`, `coding`, `heavy`, `utility`)
- response metadata / route visibility

Contract:
Codex proposes. Spot Core applies.
Spot Core holds the keys. Everything else asks permission.

Goal:
Spot becomes practically usable as an engineering assistant before mutation/apply workflows are widened.

---

# PHASE 2 — BUILD SPOT AUTONOMY

Spot must begin detecting and responding to issues inside approved guardrails.

Build:
- incident engine
- remediation classes
- safe self-fix logic
- autonomous action logs

Goal:
Spot = operations brain, not only manual router.

---

# PHASE 3 — SPOT AS BUILD ASSISTANT

Tie together:
- Spot core
- Spot UI
- Codex
- worker-03 engineering lane
- git checkpoint workflow
- proposal/apply engineering loop

Goal:
Spot helps inspect, patch, validate, and build future layers.

---

# PHASE 4 — BUILD STARFLEET OS CORE

Construct the real integrated command environment.

---

# PHASE 5 — BUILD STARFLEET HA SECURITY SYSTEM

Unified home/office security collective on top of Starfleet OS.

---

# PHASE 6 — LONG RANGE EXPANSION

Expansion only after core maturity.

---

# CURRENT ACTIVE PHASE

Current active lane:

PHASE 1.5 — SPOT ASSISTANT CLIENT SURFACE
