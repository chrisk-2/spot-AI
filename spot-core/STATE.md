# SPOT FLEET STATE

## 2026-04-30 Milestone B / GPU topology checkpoint

Milestone B operator surface is live and validated through MCP.

Confirmed in current runtime:

- `admin_operator_command status` returns Spot status successfully.
- `admin_operator_command validate` returns PASS with pass=18 warn=1 fail=0.
- `admin_operator_command routing` works and returns strict role ownership.
- `admin_operator_command audit` works and routing audit remains clean.
- `admin_operator_command latency` works.
- `admin_operator_command quarantine_state` works.
- `admin_operator_command readiness` now works through live `/operator/readiness` endpoint.
- `/operator/readiness` reports `ready_with_warnings`, not failure.
- readiness warning is currently limited to worker-02 utility latency.
- routing audit window remains clean: 200 primary, 0 fallback, 0 violations, 0 manual overrides.
- all four workers are healthy, eligible, not quarantined, and not degraded.

Readiness endpoint change:

- `spotcore/app.py` now exposes `/operator/readiness` as a live computed endpoint.
- MCP `readiness` operator command now curls `http://127.0.0.1:8787/operator/readiness` instead of requiring `/var/www/html/spot/operator-readiness.json`.
- This avoids stale or missing static readiness artifacts for MCP operator readiness.

Known active performance warning:

- worker-02 utility lane is healthy but slow.
- observed worker-02 latency: p50 about 6s, average about 8.2s, about 27.8 tok/sec.
- root cause is not CPU saturation; worker-02 inspected with near-zero load and active Ollama.
- likely cause is current topology: worker-02 utility and watcher roles share one modeled Ollama lane and default to `phi3.5:latest`.

Current physical GPU map before pending hardware changes:

- worker-01: RTX 3060 12GB
- worker-02: Quadro M4000 8GB + GTX 1060 6GB
- worker-03: GTX 1070 8GB + RTX 3060 12GB
- worker-04: Titan Xp 12GB

Current modeled routing debt:

- worker-02 currently has two physical GPUs but Spot config models it as one generic Ollama lane.
- worker-03 has two physical GPUs and is modeled with two logical gpu routes, but still one worker-level Ollama base URL.
- With one Ollama endpoint per multi-GPU host, Spot can label lanes but cannot fully enforce physical GPU selection unless Ollama is GPU-pinned per service/container.
- worker-02 needs this fixed sooner because it is already latency-warning.
- worker-03 can be deferred because it is currently healthy and fast.

Future hardware plan, not yet applied:

- Quadro P6000 24GB expected later.
- Planned placement: P6000 to worker-04 as heavy primary.
- Displaced worker-04 Titan Xp 12GB should move to worker-02, preferably replacing GTX 1060 6GB.
- If Titan Xp does not physically fit beside M4000, replace M4000 instead and leave GTX 1060 for embeddings/watcher-only use.
- If a second P6000 is acquired, reassess before changing topology.

Target future topology after hardware is installed and verified:

- worker-01 RTX 3060 12GB: general / backup heavy
- worker-02 M4000 8GB: watcher / embeddings / light utility
- worker-02 Titan Xp 12GB: utility primary
- worker-03 GTX 1070 8GB: coding small lane
- worker-03 RTX 3060 12GB: coding primary / heavy burst
- worker-04 P6000 24GB: heavy primary

Important implementation note:

- Do not blindly split worker-02 into `gpu0` and `gpu1` config lanes until actual GPU order and Ollama pinning are verified.
- Preferred clean future design is logical workers per pinned Ollama service, e.g. `spot-worker-02a` on port 11434 and `spot-worker-02b` on port 11435, each with `CUDA_VISIBLE_DEVICES` pinned.
- Same pattern may later apply to worker-03 if real workload reveals scheduling/performance mismatch.

Next active build objective:

- Continue as if P6000 does not exist yet.
- Build Milestone D.1: `spot ask` and `spot propose` assistant client surface over current stable Spot Core.
- Hardware upgrades are future config deltas, not blockers.

---

## Historical state before 2026-04-30 checkpoint

See git history and prior STATE.md revisions for older restore/self-heal/Milestone A details.
