# SPOT CORE STATE — 2026-05-05

## CURRENT STATUS

Spot Core stable.
Fleet validation passing.
Primary routing ownership intact.
Git tree clean at last checkpoint.

Current commit:
- 60daec0 worker05: add guarded standby registration draft

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

Status: ACTIVE, NON-MUTATING CONTROL STACK BASELINE THROUGH PHASE 2.14

Immediate next active step while waiting for worker-04 GPU hardware:

PHASE 2.15 — EXECUTOR PREFLIGHT LIFECYCLE/OPERATOR SURFACE

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

This is a control and audit stack only.
It does not dispatch plugins.
It does not mutate live systems.
It does not bind backups for mutation.
It does not enable autonomous execution.

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

PHASE 2.15 — EXECUTOR PREFLIGHT LIFECYCLE/OPERATOR SURFACE

Recommended scope:
- expose executor preflight create/list/show/verify through the operator surface
- add lifecycle/audit visibility for executor preflight artifacts
- preserve dry-run only behavior
- require all execution/mutation flags false
- no service restarts
- no config writes
- no network mutation
- no backup binding for mutation yet
- no executor dispatch

Do not enable mutation plugins until a future reviewed slice explicitly implements:
- backup binding
- precheck validation
- postcheck validation
- rollback contract
- append-only action logs
- explicit plugin allowlist

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
