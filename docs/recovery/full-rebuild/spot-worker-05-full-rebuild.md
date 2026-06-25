# Full rebuild runbook - spot-worker-05

## Baseline

- Worker: spot-worker-05
- Role: review
- GPU baseline: 2x Tesla P100 16GB
- Status: validated live

## Required models

- deepseek-r1:32b
- qwen2.5-coder:32b
- deepseek-r1:14b
- qwen2.5-coder:7b
- qwen2.5:32b
- qwen2.5-coder:14b
- qwen2.5:14b
- llama3.1:8b

## Notes

Review node is already fully populated. Do not run apply unless rebuilding.

## Commands

Dry-run from spot-core: cd ~/spot-stack && provision/provision-worker.sh spot-worker-05
Apply from spot-core after OS/bootstrap recovery only: cd ~/spot-stack && provision/provision-worker.sh spot-worker-05 --apply
Validate from spot-core: ssh -o BatchMode=yes -o ConnectTimeout=8 spot-worker-05 'hostname; systemctl is-active ssh; systemctl is-active ollama; nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader; ollama list; findmnt /mnt/collective || true'

## Stop conditions

- Hostname mismatch.
- SSH inactive or unreachable.
- Ollama inactive.
- NVIDIA missing or wrong GPU.
- Required model missing after provision apply.
- /mnt/collective unavailable when required.
- W-06 apply attempted before restore_deferred is cleared.
