# SPOT CORE STATE — 2026-05-03

## CURRENT STATUS
Spot Core stable.
Fleet validation passing.
Primary routing ownership intact.

Validation baseline:
- pass=19
- warn=0
- fail=0
- RESULT: PASS

---

## COMPLETED THIS SESSION

### 1. spot-worker-05 commissioned to pre-GPU ready state
New worker node prepared and online:

- hostname: spot-worker-05
- ip: 192.168.10.15
- chassis: Equus Nobilis
- board: ASUS PRIME Z390-A
- cpu: i7-8700
- storage: NVMe
- os: Ubuntu 24.04
- ollama installed/running
- docker installed/running
- /mnt/collective mounted
- /mnt/unimatrix6 mounted
- local FastAPI health endpoint active on :8755

Pending hardware:
- Quadro P6000 install
- RAM upgrade to 64GB target
- NVIDIA production driver

Role planned:
- heavy-secondary
- research
- staging

---

### 2. PHASE 1.7 utility regression resolved
Resolved utility lane operator + validator instability:

- spot ask no longer injects Durable Memory by default
- spot ask --memory explicitly enables memory context
- spot propose behavior preserved
- worker-02 utility lane phi3.5 Ollama degradation identified
- targeted ollama.service restart on worker-02 restored utility validation responsiveness

Post-remediation:
spot validate => PASS

---

### 3. PHASE 1.7 artifact semantics contract patch applied
watch/spot-client.sh full-file rewrite completed successfully.

Apply-plan artifacts now emit:

- policy_class: supervised_apply_plan
- autonomy_level: 1
- execution_wrapper_required: true
- executor: spot-core-controlled-wrapper
- approval_gate: human_review_required
- rollback_required: true
- rollback_authority: recorded_prechange_backup_only

Execution-handoff artifacts now emit:

- policy_class: controlled_execution_handoff
- autonomy_level: 1
- execution_wrapper_required: true
- executor: spot-core-controlled-wrapper
- approval_gate: wrapper_execution_approval_required
- rollback_required: true
- rollback_authority: recorded_prechange_backup_only

Status readers now surface these fields.

Validation after patch:
spot validate => PASS

Manual pre-contract backup created:
- /mnt/collective/backups/spot-core/manual/

---

## ACTIVE PHASE
PHASE 1.7 — SUPERVISED APPLY-PLAN ENGINE

Current remaining open item:
- strengthen artifact verifiers so apply-plan and execution-handoff validation REQUIRE the new contract metadata fields, not merely emit them

No autonomous mutation capability enabled.
Mutation remains blocked.
execution_allowed remains false.
backup_bound remains false.

---

## FLEET SNAPSHOT

worker-01 = general
worker-02 = utility
worker-03 = coding
worker-04 = heavy-primary
worker-05 = heavy-secondary commissioning/pre-GPU


---

## 2026-05-03 WORKER-05 GPU BRING-UP CHECKLIST

spot-worker-05 is pre-commissioned and ready for GPU installation.

Current ready state:
- hostname: spot-worker-05
- IP: 192.168.10.15
- OS: Ubuntu 24.04
- CPU: i7-8700
- board: ASUS PRIME Z390-A
- current RAM: 16GB DDR4 2400, 4x4GB
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

Expected health after GPU:
- gpu_info should show Quadro P6000
- collective_mounted true
- unimatrix6_mounted true
- ollama active
- docker active

Do not add worker-05 to production routing until:
- NVIDIA driver is stable
- thermals are acceptable
- Ollama can run a test model
- health endpoint reports GPU
- RAM upgrade plan is confirmed or installed
