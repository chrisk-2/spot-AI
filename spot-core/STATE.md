# SPOT CORE STATE — 2026-05-04

## CURRENT STATUS

Spot Core stable.
Fleet validation passing.
Primary routing ownership intact.
Git tree clean at last checkpoint.

Current commit:
- 983a7c8 phase213: add plugin request lifecycle and audit

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

Status: ACTIVE, NON-MUTATING CONTROL STACK BASELINE THROUGH PHASE 2.13

Phase 2 is building controlled autonomy rails without enabling autonomous mutation.

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

This is a control and audit stack only.
It does not dispatch plugins.
It does not mutate live systems.
It does not bind backups for mutation.
It does not enable autonomous execution.

---

## IMPORTANT ARTIFACTS

Policy manifest:
- /home/ogre/spot-stack/watch/policy/action-policy.json

Plugin registry:
- /home/ogre/spot-stack/watch/policy/plugin-registry.json

Sample closed action request:
- /home/ogre/spot-stack/watch/action-requests/ACTION-20260504-153133-read_only_diagnostic-spot-core.json

Sample closed action handoff:
- /home/ogre/spot-stack/watch/action-handoffs/ACTION-HANDOFF-20260504-160158-ACTION-20260504-160153-read_only_diagnostic-spot-core.json

Sample closed plugin request:
- /home/ogre/spot-stack/watch/plugin-requests/PLUGIN-REQUEST-20260504-164220-read_only_status_probe-ACTION-HANDOFF-20260504-160158-ACTION-20260504-160153-read_only_diagnostic-spot-core.json

Phase 1.7 canonical run:
- RUN-HANDOFF-APPLY-phase17-lifecycle-test-041538-20260504-030310

---

## NEXT ENGINEERING LANE

Next candidate:

PHASE 2.14 — EXECUTOR DRY-RUN PREFLIGHT CONTRACT

Recommended scope:
- define executor preflight contract artifact
- require plugin request verification
- require registry verification
- require action policy verification
- require dry-run only
- require all execution/mutation flags false
- produce preflight artifact only
- no service restarts
- no config writes
- no network mutation
- no backup binding for mutation yet

Do not enable mutation plugins until a future reviewed slice explicitly implements:
- backup binding
- precheck validation
- postcheck validation
- rollback contract
- append-only action logs
- explicit plugin allowlist

---

## FLEET SNAPSHOT

worker-01 = general
worker-02 = utility, healthy but latency warning-level
worker-03 = coding
worker-04 = heavy-primary
worker-05 = heavy-secondary commissioning/GPU-validated/pre-routing

Latest observed checkpoint trend:
- worker-01 healthy and fast
- worker-02 healthy but slow, p50 around 10–12s in recent checkpoints
- worker-03 healthy and fast
- worker-04 healthy and fast

---

## WORKER-05 GPU BRING-UP CHECKLIST

spot-worker-05 has Quadro P6000 installed and GPU smoke validated. It remains pre-routing.

Current ready state:
- hostname: spot-worker-05
- IP: 192.168.10.15
- OS: Ubuntu 24.04
- CPU: i7-8700
- board: ASUS PRIME Z390-A
- RAM target: 64GB DDR4 UDIMM non-ECC
- storage: NVMe
- /mnt/collective mounted
- /mnt/unimatrix6 mounted
- Docker active
- Ollama active
- health API active on port 8755

GPU status:
- Quadro P6000 installed
- NVIDIA driver 535.288.01 active
- nvidia-smi reports Quadro P6000 with 23040 MiB VRAM
- Ollama llama3.1:8b GPU smoke test passed
- health endpoint reports GPU info
- still not registered into Spot production routing

Post-GPU commands on worker-05:
  ~/worker05_post_gpu.sh
  sudo reboot
  nvidia-smi
  ~/worker05_health.sh
  curl -s http://127.0.0.1:8755/health | jq

Do not add worker-05 to production routing until a separate reviewed registration slice updates inventory, health checks, role assignment, and routing policy.
