# Full rebuild runbook - spot-worker-01

## Baseline

- Worker: spot-worker-01
- Role: general
- GPU baseline: RTX 3060 12GB
- Status: validated live

## Required models

- mistral:7b
- llama3.1:8b

## Notes

Extra installed models are allowed but not required.

## Commands

Dry-run from spot-core: cd ~/spot-stack && provision/provision-worker.sh spot-worker-01
Apply from spot-core after OS/bootstrap recovery only: cd ~/spot-stack && provision/provision-worker.sh spot-worker-01 --apply
Validate from spot-core: ssh -o BatchMode=yes -o ConnectTimeout=8 spot-worker-01 'hostname; systemctl is-active ssh; systemctl is-active ollama; nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader; ollama list; findmnt /mnt/collective || true'

## Stop conditions

- Hostname mismatch.
- SSH inactive or unreachable.
- Ollama inactive.
- NVIDIA missing or wrong GPU.
- Required model missing after provision apply.
- /mnt/collective unavailable when required.
- W-06 apply attempted before restore_deferred is cleared.
