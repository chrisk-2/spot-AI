# STARFLEET HANDOFF — 2026-05-05

Read spot-core/STATE.md first.

---

## SAFE RESUME POINT

System stable.
Fleet validate currently PASS.
Git tree should be committed after this docs update.

Current active lane:
- PHASE 2 — BUILD SPOT CONTROLLED AUTONOMY

Phase 1.7 is complete and baseline locked.
Phase 2.1 through Phase 2.28 are complete and non-mutating.
Worker-05 standby/manual integration is complete and non-routing.

No active regression recovery is in progress.
No autonomous mutation is enabled.
No plugin dispatch is enabled.
No worker-05 automatic routing is enabled.

---

## CURRENT CHECKPOINT

Latest completed worker-05 checkpoint:
- 60daec0 worker05: add guarded standby registration draft

Validated:
- action-policy-verify PASS
- plugin-registry-verify PASS
- plugin request verifier PASS
- worker05-verify PASS
- worker05-routing-guard PASS
- worker05-standby-draft-verify PASS
- spot validate PASS, pass=19 warn=0 fail=0

Runtime posture:
- mutation_plugins_enabled=false
- plugin_execution_enabled=false
- plugin_execution_allowed=false
- execution_allowed=false on control artifacts
- mutation_allowed=false on control artifacts
- mutation_performed=false on control artifacts
- worker-05 routing_enabled=false
- worker-05 primary=false
- worker-05 production_role=none

---

## COMPLETED CONTROL STACK

Completed Phase 2 slices:

- 2.1 execution-run lifecycle
- 2.2 execution-run read-only visibility
- 2.3 action policy manifest
- 2.4 action policy verifier
- 2.5 non-executing action request artifacts
- 2.6 action request lifecycle
- 2.7 action request audit/summary
- 2.8 non-executing action handoff bridge
- 2.9 action handoff lifecycle/audit
- 2.10 disabled plugin registry manifest
- 2.11 plugin registry audit/summary
- 2.12 non-executing plugin request artifacts
- 2.13 plugin request lifecycle/audit
- 2.14 executor dry-run preflight contract
- 2.15 executor preflight lifecycle/operator surface
- 2.16 executor preflight failure-path validation
- 2.18 backup-binding contract design
- 2.19 backup-binding contract operator surface
- 2.20 backup-binding contract summary/failure validation
- 2.22 backup artifact manifest contract design
- 2.23 backup artifact manifest operator surface
- 2.24 backup artifact manifest summary/failure validation
- 2.26 backup artifact manifest implementation dry-run simulator
- 2.27 backup artifact manifest dry-run operator surface
- 2.28 backup artifact manifest dry-run summary/failure validation

Current chain:

1. action policy manifest
2. policy verifier
3. action request artifact
4. action request verifier
5. action request lifecycle
6. action request audit/summary
7. non-executing action handoff candidate
8. action handoff verifier
9. action handoff lifecycle
10. action handoff audit/summary
11. disabled plugin registry manifest
12. plugin registry verifier
13. plugin registry audit/summary
14. non-executing plugin request artifact
15. plugin request verifier
16. plugin request lifecycle
17. plugin request audit/summary
18. executor dry-run preflight contract
19. executor preflight lifecycle/operator surface
20. executor preflight failure-path validation
21. backup-binding contract design
22. backup-binding contract operator surface/summary
23. backup-binding contract failure-path validation
24. backup artifact manifest contract design
25. backup artifact manifest operator surface/summary
26. backup artifact manifest failure-path validation
27. backup artifact manifest dry-run simulator
28. backup artifact manifest dry-run operator surface/summary
29. backup artifact manifest dry-run failure-path validation

This is still a control/audit chain only.

---

## WORKER-05 STATUS

worker-05 is fully prepared as a validated standby/manual node.

Current classification:

```text
spot-worker-05 = heavy-secondary / standby / burst-candidate / fallback-candidate
routing_enabled = false
primary = false
production_role = none
manual ask = allowed through worker05-ask only
```

Completed worker-05 work:
- GPU install validated
- NVIDIA driver 535.288.01 active
- Quadro P6000 visible with 23040 MiB VRAM
- Ollama GPU smoke passed
- remote Ollama API passed
- remote GPU inference confirmed
- passwordless SSH from core passed
- passwordless sudo from core passed
- health endpoint status corrected to gpu_validated_pre_routing
- commissioning runbook added
- non-routing inventory added
- standby health verifier added
- standby routing guard added
- manual worker05-ask added
- guarded standby registration draft added

Important files:
- /home/ogre/spot-stack/WORKER-05-COMMISSIONING.md
- /home/ogre/spot-stack/watch/inventory/worker-05.json
- /home/ogre/spot-stack/watch/standby-registration/WORKER05-STANDBY-DRAFT-20260505-002114.json

Worker-05 commands:
- watch/spot-client.sh worker05-status
- watch/spot-client.sh worker05-verify
- watch/spot-client.sh worker05-routing-guard
- watch/spot-client.sh worker05-ask <prompt>
- watch/spot-client.sh worker05-standby-drafts [count]
- watch/spot-client.sh show-worker05-standby-draft <id-or-file>
- watch/spot-client.sh worker05-standby-draft-verify <id-or-file>

Do not add worker-05 to automatic routing until a separate reviewed routing slice adds router enforcement for enabled/eligible/routing_enabled/manual_only.

---

## ACTIVE PRODUCTION ROUTING

Production primaries remain:

```text
general -> spot-worker-01
utility -> spot-worker-02
coding  -> spot-worker-03
heavy   -> spot-worker-04
```

worker-05 is not production-routed.

---

## WORKER-04 GPU UPGRADE NEXT HARDWARE PATH

worker-04 remains heavy primary.
Its new GPU is expected next.

After worker-04 new GPU is installed:

1. Keep heavy primary on worker-04.
2. Do not promote worker-05 automatically.
3. Validate worker-04 hardware and driver:
   - lspci | egrep -i 'nvidia|vga|3d|display'
   - nvidia-smi
   - nvidia-smi --query-gpu=index,name,memory.total,memory.free,temperature.gpu,power.draw,driver_version --format=csv,noheader,nounits
4. Validate nvidia-persistenced.
5. Validate Ollama.
6. Run local Ollama GPU smoke.
7. Validate remote health and remote Ollama from spot-core.
8. Run spot validate.
9. Update STATE.md, HANDOFF.md, ROADMAP.md, and any worker-04 runbook/checkpoint.

Post-GPU worker-04 result should be:

```text
heavy -> spot-worker-04
worker-05 -> heavy-secondary standby/manual-only
```

---

## NEXT ACTIVE ENGINEERING LANE WHILE WAITING

Resume Phase 2, not routing.

Next slice:

PHASE 2.29 — READINESS GATE DECISION CHECKPOINT

Completed since prior handoff:
- Phase 2.26 added the backup artifact manifest dry-run simulator artifact lane.
- Phase 2.27 exposed backup artifact manifest dry-run create/list/show/verify through `watch/spot-ops.sh`.
- Phase 2.28 added backup artifact manifest dry-run summary generation.
- Phase 2.28 added failure-path validation and rejected 30 unsafe backup artifact manifest dry-run variants.
- All execution/mutation/plugin dispatch/service restart/config write/network mutation/live file read/live hashing/live backup creation/live backup binding/checksum generation gates remain false.
- Successful backup artifact manifest dry-run artifacts report ok=true and blocked=true by design.

Recommended next scope:
- define a go/no-go readiness checkpoint for future live backup work
- aggregate proof from executor preflight, backup-binding contract, manifest contract, and manifest dry-run lanes
- verify all known summaries are clean
- verify all failure-path harnesses pass
- produce checkpoint artifact only
- preserve dry-run only behavior
- no service restarts
- no config writes
- no network mutation
- no live backup creation
- no live backup binding
- no live source file reads
- no live source file hashing
- no real checksum generation over live files
- no executor dispatch

Do not proceed to live backup creation, live backup binding, checksum generation over live files, live source file reads, live source file hashing, or real executor behavior until the readiness gate checkpoint is committed and reviewed.

---

## PROJECT RULES STILL LOCKED

No backup, no change.
No autonomous mutation.
No freeform shell mutation.
No backup deletion or overwrite.
No network/firewall/DNS/DHCP/VLAN/routing mutation.
No plugin execution until an explicit future reviewed slice enables a narrow allowlisted plugin.
No worker-05 automatic traffic until explicit routing enablement.

Memory and proposal history remain context only, not authorization.
Rollback authority remains recorded_prechange_backup_only.

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
