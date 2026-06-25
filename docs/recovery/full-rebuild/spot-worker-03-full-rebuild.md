# Full rebuild runbook - spot-worker-03

## Baseline

- Worker: spot-worker-03
- Role: coding
- GPU baseline: GTX 1070 8GB + RTX 3060 12GB
- Status: validated live

## Required models

- qwen2.5-coder:7b
- codellama:7b
- deepseek-coder:6.7b

## Notes

qwen2.5:14b is no longer required for this worker.

## Commands

Dry-run from spot-core: cd ~/spot-stack && provision/provision-worker.sh spot-worker-03
Apply from spot-core after OS/bootstrap recovery only: cd ~/spot-stack && provision/provision-worker.sh spot-worker-03 --apply
Validate from spot-core: ssh -o BatchMode=yes -o ConnectTimeout=8 spot-worker-03 'hostname; systemctl is-active ssh; systemctl is-active ollama; nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader; ollama list; findmnt /mnt/collective || true'

## Stop conditions

- Hostname mismatch.
- SSH inactive or unreachable.
- Ollama inactive.
- NVIDIA missing or wrong GPU.
- Required model missing after provision apply.
- /mnt/collective unavailable when required.
- W-06 apply attempted before restore_deferred is cleared.
