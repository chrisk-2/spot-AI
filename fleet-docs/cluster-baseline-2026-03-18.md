# Starfleet Cluster Baseline — 2026-03-18

## Status
This document captures the last known-good baseline for the Starfleet cluster after Spot stabilization, reboot validation, policy-driven audit update, and snapshot automation.

## Stable Git Commit
- Commit: `9d834d6`
- Message: `Make fleet audit policy-driven`

## Spot Core Services
The following services are expected to be enabled and active on Spot:

- `spot-gateway.service`
- `spot-worker.service`
- `spot-worker0.service`

### Service Roles
- `spot-gateway.service`
  - Main gateway and scheduler entrypoint
  - Health URL: `http://127.0.0.1:8798/health`

- `spot-worker.service`
  - Local wrapper / queue watcher service
  - Watches local work inbox

- `spot-worker0.service`
  - Actual Spot GPU worker API
  - Bound locally on `127.0.0.1:8787`

## Cluster Worker Roles

### Exec Pool
- `spot_exec`
  - Host: Spot
  - GPU: NVIDIA GeForce RTX 3060 12GB
  - Role: primary general/light inference
  - Forced class: `14b`

- `daystrom_exec`
  - Host: Daystrom
  - GPU: NVIDIA GeForce RTX 3060 12GB
  - Role: coder workloads

- `m5_exec`
  - Host: M-5
  - GPU: Quadro M4000 8GB
  - Role: utility / background inference

### Watch / Utility Nodes
- `m5_watch`
  - Host: M-5
  - GPU: GTX 1060 6GB
  - Role: heartbeat / tiny jobs

- `daystrom_watch`
  - Host: Daystrom
  - GPU: GTX 1070 8GB
  - Role: reserve / watch capacity

## Routing Policy Baseline
Expected dispatch behavior:

- `light` -> `spot_exec`
- `coder` -> `daystrom_exec`
- `14b` -> `spot_exec`
- `tiny` -> `m5_watch`
- `heartbeat` -> `m5_watch`

Policy mode:
- `preferred_order`

## Policy File
Tracked policy file:
- `configs/node-policy.env`

Current policy expectations:
- `SPOT_GATEWAY_UNIT=spot-gateway`
- `SPOT_WORKER_UNIT=spot-worker0`
- `M5_HOST=192.168.10.11`
- `DAYSTROM_HOST=192.168.10.13`
- `GATEWAY_HEALTH_URL=http://127.0.0.1:8798/health`

## Validation Performed

### Reboot Survival
Validated after reboot:
- `spot-gateway`: active and enabled
- `spot-worker`: active and enabled

### Fleet Status
Known-good `fleet` output characteristics:
- core services OK
- warnings: none
- dispatch tests all PASS
- heartbeat PASS on `m5_watch`

### Audit
Audit script:
- `scripts/starfleet-audit.sh`

Audit result:
- `AUDIT PASS`

## Snapshot Automation
Snapshot script:
- `scripts/fleet-save-state.sh`

Known-good snapshot created:
- Directory:
  - `/home/ogre/spot-AI/fleet-docs/snapshots/2026-03-18_230157`
- Archive:
  - `/home/ogre/spot-AI/fleet-docs/snapshots/2026-03-18_230157.tar.gz`

## Operational Ritual
After any routing, worker, gateway, or model change, run:

```bash
fleet
~/spot-AI/scripts/starfleet-audit.sh
~/spot-AI/scripts/fleet-save-state.sh
