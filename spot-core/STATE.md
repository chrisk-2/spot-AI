# SPOT CORE STATE — 2026-05-04

## CURRENT STATUS
Spot Core stable.
Fleet validation passing.
Primary routing ownership intact.

Validation baseline:
- pass=19
- warn=0
- fail=0
- RESULT: PASS

Current commit:
- 4e17214 phase17: prove supervised execution dry-run lifecycle

---

## CURRENT ACTIVE LANE

PHASE 1.7 — SUPERVISED APPLY-PLAN ENGINE

Status: COMPLETE / BASELINE LOCKED

Phase 1.7 is now functionally complete for the supervised dry-run scope. It proves the handoff-to-wrapper path without enabling mutation.

Verified proof run:
- RUN-HANDOFF-APPLY-phase17-lifecycle-test-041538-20260504-030310

Verified gates:
- execution handoff verification passes
- supervised dry-run wrapper runs through bash from spot-client.sh
- execution-run artifact generated
- precheck log generated
- backup artifact created under /mnt/collective/backups/spot-core/supervised-apply/
- handoff, apply plan, proposal, and target file copied into backup artifact
- SHA256SUMS generated and verified
- run_status: prepared_backup_bound_dry_run
- execution_allowed: false
- mutation_allowed: false
- mutation_performed: false
- backup_bound: true
- backup_verified: true
- spot validate passes after lifecycle proof

Policy posture:
- no backup, no change enforced for dry-run wrapper
- mutation plugin dispatch remains disabled
- high-risk network actions remain gated
- memory and proposal history remain context only, not authorization
- rollback authority remains recorded_prechange_backup_only

---

## COMPLETED THIS SESSION

### 1. PHASE 1.7 supervised dry-run execution wrapper proven

Completed:
- watch/spot-apply.sh supervised dry-run wrapper
- spot-client.sh handoff execution command wiring
- execution-runs listing/show/verify commands
- lifecycle test proposal fixture
- lifecycle test apply-plan fixture
- lifecycle test handoff risk normalized to low
- verified backup-bound dry-run artifact creation
- verified SHA256 backup integrity
- verified mutation remains disabled

Important fix:
- spot-client.sh now invokes spot-apply.sh through bash instead of relying on executable filesystem metadata. Git mode is 100755, but live filesystem behavior made direct -x checks unreliable.

Commit:
- 4e17214 phase17: prove supervised execution dry-run lifecycle

Result:
- watch/spot-client.sh execution-run-verify RUN-HANDOFF-APPLY-phase17-lifecycle-test-041538-20260504-030310 => PASS
- spot validate => PASS, pass=19 warn=0 fail=0

---

### 2. spot-worker-05 commissioned to pre-GPU ready state

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

### 3. PHASE 1.7 utility regression resolved

Resolved utility lane operator + validator instability:

- spot ask no longer injects Durable Memory by default
- spot ask --memory explicitly enables memory context
- spot propose behavior preserved
- worker-02 utility lane phi3.5 Ollama degradation identified
- targeted ollama.service restart on worker-02 restored utility validation responsiveness

Post-remediation:
spot validate => PASS

---

## FLEET SNAPSHOT

worker-01 = general
worker-02 = utility, healthy but latency warning-level
worker-03 = coding
worker-04 = heavy-primary
worker-05 = heavy-secondary commissioning/pre-GPU

Latest observed latency snapshot from checkpoint:
- worker-01 p50 around 1127 ms
- worker-02 p50 around 14941 ms
- worker-03 p50 around 1731 ms
- worker-04 p50 around 1354 ms

worker-02 remains the known latency laggard. Do not tune worker-02 until after the planned GPU reshuffle unless a new failure appears.

---

## NEXT ENGINEERING LANE

Do not reopen Phase 1.7 unless a fresh regression appears.

Next safe direction:
- move to the next roadmap lane after Phase 1.7 baseline lock
- begin controlled-autonomy design from the proven supervised dry-run wrapper
- keep mutation plugins disabled until explicit Phase 2 design and policy review

Immediate useful cleanup before Phase 2:
- commit support document updates
- optional UX improvement: add visible progress markers in spot-apply.sh prechecks
- remove or classify stray untracked top-level apply-plans/ if it is accidental

---

## WORKER-05 GPU BRING-UP CHECKLIST

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
