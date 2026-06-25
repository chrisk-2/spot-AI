# Starfleet full worker rebuild runbooks

These runbooks define from-scratch worker recovery using the Starfleet provisioning layer.

Source of truth:
- spot-core/config/cluster_config.json
- watch/fleet-policy.json
- inventory/roles.json
- provision/bootstrap-worker.sh
- provision/provision-worker.sh

General rebuild sequence:
1. Boot replacement hardware.
2. Install Ubuntu Server.
3. Set hostname to the exact worker name.
4. Copy provision/bootstrap-worker.sh from spot-core to the worker.
5. Run bootstrap-worker.sh on the worker with --apply.
6. Run provision/provision-worker.sh from spot-core.
7. Validate SSH, Ollama, NVIDIA, required models, and /mnt/collective.

Worker-06 is intentionally deferred and must not be applied until it is back online and backed up.
