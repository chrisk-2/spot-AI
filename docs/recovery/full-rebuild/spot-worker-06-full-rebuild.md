# Full rebuild runbook - spot-worker-06

## Baseline

- Worker: spot-worker-06
- Role: reasoning
- GPU baseline: Quadro P6000 23GB
- Status: deferred

## Required models

- None while deferred.

## Notes

provision_enabled=false and restore_deferred=true until node is back and backed up.

## Commands

Dry-run from spot-core: cd ~/spot-stack && provision/provision-worker.sh spot-worker-06

Apply is blocked by policy while this node is deferred.
Expected dry-run result: SKIP because provision_enabled=false.

## Stop conditions

- Hostname mismatch.
- SSH inactive or unreachable.
- Ollama inactive.
- NVIDIA missing or wrong GPU.
- Required model missing after provision apply.
- /mnt/collective unavailable when required.
- W-06 apply attempted before restore_deferred is cleared.
