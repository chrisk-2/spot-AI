# Full rebuild runbook - spot-worker-04

## Baseline

- Worker: spot-worker-04
- Role: heavy
- GPU baseline: Quadro P6000 24GB
- Status: validated live

## Required models

- qwen2.5:14b

## Notes

/mnt/ai-data and /mnt/collective were validated.

## Commands

Dry-run from spot-core: cd ~/spot-stack && provision/provision-worker.sh spot-worker-04
Apply from spot-core after OS/bootstrap recovery only: cd ~/spot-stack && provision/provision-worker.sh spot-worker-04 --apply
Validate from spot-core: ssh -o BatchMode=yes -o ConnectTimeout=8 spot-worker-04 'hostname; systemctl is-active ssh; systemctl is-active ollama; nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader; ollama list; findmnt /mnt/collective || true'

## Stop conditions

- Hostname mismatch.
- SSH inactive or unreachable.
- Ollama inactive.
- NVIDIA missing or wrong GPU.
- Required model missing after provision apply.
- /mnt/collective unavailable when required.
- W-06 apply attempted before restore_deferred is cleared.
