# WORKER-05 COMMISSIONING RUNBOOK

## Current status

worker-05 is prepared, GPU-validated, remotely reachable, and pre-routing.

It is not part of production Spot routing yet.

Current classification:

```text
spot-worker-05 = GPU-validated / pre-routing / no production role
```

---

## Identity

```text
hostname: spot-worker-05
ip: 192.168.10.15
dns_or_hosts_status: resolvable from spot-core as spot-worker-05
passwordless_ssh_from_core: true
routing_enabled: false
production_role: none
planned_role: heavy-secondary / research / staging / burst candidate
```

---

## Hardware status

```text
GPU: Quadro P6000
GPU PCI ID: NVIDIA GP102GL [Quadro P6000]
Driver: NVIDIA 535.288.01
CUDA reported by nvidia-smi: 12.2
VRAM reported: 23040 MiB
nvidia-persistenced: active
```

Driver note:
- NVIDIA 595 DKMS installed but did not bind to the P6000.
- NVIDIA 535.288.01 resolved nvidia-smi and persistence daemon.

---

## GPU smoke proof

Local Ollama GPU smoke test passed with:

```bash
ollama pull llama3.1:8b
ollama run llama3.1:8b "Reply with exactly: worker-05 gpu smoke pass"
```

Observed response:

```text
worker-05 gpu smoke pass
```

During the local test, nvidia-smi showed Ollama resident on the P6000:

```text
GPU memory: about 5374 MiB / 23040 MiB
Process: /usr/local/bin/ollama
```

---

## Remote validation from spot-core

Passwordless SSH from spot-core passed:

```bash
ssh -o BatchMode=yes spot-worker-05 'hostname; whoami; nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader'
```

Observed:

```text
spot-worker-05
ogre
Quadro P6000, 23040 MiB, 535.288.01
```

Remote health API passed:

```bash
curl -s http://spot-worker-05:8755/health | jq
```

Observed health fields:

```text
worker_id: spot-worker-05
collective_mounted: true
unimatrix6_mounted: true
gpu_info: Quadro P6000, 23040 MiB
```

Remote Ollama API passed:

```bash
curl -s http://spot-worker-05:11434/api/tags | jq
```

Remote inference passed:

```bash
curl -sS --max-time 120 http://spot-worker-05:11434/api/generate \
  -H 'Content-Type: application/json' \
  -d '{"model":"llama3.1:8b","prompt":"Say hello from worker 05 in five words.","stream":false}'
```

Observed response:

```text
Hello, this is worker number 5.
```

Remote inference used the P6000:

```text
process: /usr/local/bin/ollama
used_memory: about 5372 MiB
```

---

## Services

Validated:

```text
ollama: active
nvidia-persistenced: active
health API: active on 127.0.0.1:8755
Ollama API: reachable from spot-core on 11434
```

Ollama binding change:

```ini
[Service]
Environment="OLLAMA_HOST=0.0.0.0:11434"
```

---

## Mounts

Validated:

```text
/mnt/collective mounted
/mnt/unimatrix6 mounted
```

Observed sources:

```text
/mnt/collective -> 192.168.50.10:/volume1/docker
/mnt/unimatrix6 -> 192.168.50.10:/volume1/spotvault
```

---

## Current blocker before production routing

worker-05 has passed hardware, GPU, SSH, health, and remote Ollama validation.

It is still not routed because production integration must be a separate reviewed slice.

Do not add worker-05 to Spot production routing until a future routing slice explicitly updates inventory, health checks, role assignment, cluster_config routing, and validation expectations.

---

## Do not route yet

Required before routing:

```text
1. Keep non-routing inventory record committed.
2. Correct worker-05 health endpoint commission_status from pre_gpu_ready to gpu_validated_pre_routing.
3. Validate health API remotely from spot-core after any service restart.
4. Validate Ollama remote model call after any Ollama config change.
5. Decide role: heavy-secondary, research, staging, or burst-only.
6. Update cluster config only in a separate reviewed routing slice.
7. Run spot validate after any production config change.
```

---

## Safe validation commands

From spot-core:

```bash
ssh -o BatchMode=yes spot-worker-05 'hostname; whoami; nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader'
curl -s http://spot-worker-05:8755/health | jq
curl -s http://spot-worker-05:11434/api/tags | jq
```

From worker-05:

```bash
nvidia-smi
systemctl is-active nvidia-persistenced
systemctl is-active ollama
ollama list
findmnt /mnt/collective
findmnt /mnt/unimatrix6
curl -s http://127.0.0.1:8755/health && echo
```

---

## Registration plan

Current completed slice:

```text
worker-05 non-routing inventory registration
```

Scope:

```text
- inventory record only
- routing_enabled=false
- production_role=none
- gpu_validated=true
- remote_health_validated=true
- remote_ollama_validated=true
- passwordless_ssh_from_core=true
- no cluster routing changes
```
