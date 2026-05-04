# SPOT CORE STATE — 2026-05-04

## CURRENT STATUS

Spot Core stable.
Fleet validation passing.
Primary routing ownership intact.
Git tree clean at last checkpoint.

Current commit:
- 77de4b6 phase29: add action handoff review lifecycle and audit

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

Status: ACTIVE, NON-MUTATING CONTROL STACK BASELINE THROUGH PHASE 2.9

Phase 2 is building controlled autonomy rails without enabling autonomous mutation.

Current safety posture:
- mutation_plugins_enabled: false
- execution_allowed remains false in generated control artifacts
- mutation_allowed remains false in generated control artifacts
- mutation_performed remains false in generated control artifacts
- backup delete/overwrite remains forbidden
- freeform shell mutation remains forbidden
- high-risk network change remains restricted/disabled
- no backup, no change remains absolute

---

## COMPLETED PHASE 2 SLICES

### Phase 2.1 — Execution-run lifecycle

Completed:
- execution-run lifecycle transitions
- manual review approve/reject/close flow
- verifier accepts lifecycle-safe run statuses

States:
- prepared_backup_bound_dry_run
- manual_review_approved
- manual_review_rejected
- closed_no_execution

---

### Phase 2.2 — Execution-run read-only visibility

Completed:
- execution-run-status
- execution-run-audit
- execution-run-summary

Purpose:
- inspect run state without dumping full artifacts
- confirm backup, precheck, lifecycle, and mutation-disabled posture

---

### Phase 2.3 — Action policy manifest

Completed:
- watch/policy/action-policy.json
- action-policy display command

Policy encodes:
- no_backup_no_change
- mutation_plugins_enabled=false
- read_only_diagnostic allowed
- supervised_dry_run allowed
- safe_service_restart planned_disabled
- controlled_config_write planned_disabled
- restore_from_backup planned_disabled
- network_change restricted_disabled
- backup_delete_or_overwrite forbidden
- freeform_shell_mutation forbidden

---

### Phase 2.4 — Action policy verifier

Completed:
- action-policy-verify

Verifier fails if policy drifts unsafe:
- mutation plugins enabled
- backup delete/overwrite allowed
- primary rule changed
- network changes ungated
- forbidden classes become mutable

---

### Phase 2.5 — Non-executing action request artifacts

Completed:
- create-action-request
- action-requests
- show-action-request
- action-request-verify

Artifact type:
- watch/action-requests/ACTION-*.json

Request artifacts remain non-executing:
- request_status=draft_non_executing initially
- execution_allowed=false
- mutation_allowed=false
- mutation_performed=false

---

### Phase 2.6 — Action request lifecycle

Completed:
- action-request-status
- approve-action-request
- reject-action-request
- close-action-request

States:
- draft_non_executing
- review_approved_non_executing
- review_rejected
- closed_no_execution

Canonical closed sample:
- ACTION-20260504-153133-read_only_diagnostic-spot-core

---

### Phase 2.7 — Action request audit/summary

Completed:
- action-request-audit
- action-request-summary

Purpose:
- operator-grade visibility for request objects
- lifecycle event visibility
- mutation-disabled posture confirmation

---

### Phase 2.8 — Non-executing action handoff bridge

Completed:
- prepare-action-handoff
- action-handoffs
- show-action-handoff
- action-handoff-status
- action-handoff-verify

Artifact type:
- watch/action-handoffs/ACTION-HANDOFF-*.json

Bridge behavior:
- approved action request produces a non-executing handoff candidate
- handoff_status=prepared_non_executing initially
- next_allowed_action=manual_review_only

Canonical handoff sample:
- ACTION-HANDOFF-20260504-160158-ACTION-20260504-160153-read_only_diagnostic-spot-core

---

### Phase 2.9 — Action handoff lifecycle/audit

Completed:
- action-handoff-audit
- action-handoff-summary
- approve-action-handoff
- reject-action-handoff
- close-action-handoff

States:
- prepared_non_executing
- review_approved_non_executing
- review_rejected
- closed_no_execution

Canonical handoff sample is now closed_no_execution with lifecycle_history.

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

This is a control and audit stack only.
It does not dispatch plugins.
It does not mutate live systems.
It does not bind backups for mutation.
It does not enable autonomous execution.

---

## NEXT ENGINEERING LANE

Next candidate:

PHASE 2.10 — CONTROLLED EXECUTOR SKELETON / PLUGIN REGISTRY MANIFEST

Recommended scope:
- define plugin registry manifest
- all plugins disabled by default
- registry verifier
- no execution path yet
- no service restarts yet
- no config writes yet
- no network mutation

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
worker-05 = heavy-secondary commissioning/pre-GPU

Latest observed checkpoint trend:
- worker-01 healthy and fast
- worker-02 healthy but slow, p50 around 12s at latest checkpoint
- worker-03 healthy and fast
- worker-04 healthy and fast

---

## WORKER-05 GPU BRING-UP CHECKLIST

spot-worker-05 remains pre-commissioned and ready for GPU installation.

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

GPU plan:
- install Quadro P6000 24GB into worker-05
- remove GT730 placeholder if needed
- install NVIDIA production driver after physical install
- verify with nvidia-smi
- run worker health check
- run Ollama model test
- only then register into Spot routing

Post-GPU commands on worker-05:
  ~/worker05_post_gpu.sh
  sudo reboot
  nvidia-smi
  ~/worker05_health.sh
  curl -s http://127.0.0.1:8755/health | jq

Do not add worker-05 to production routing until GPU, NVIDIA driver, thermals, Ollama, mounts, and health API all pass.
