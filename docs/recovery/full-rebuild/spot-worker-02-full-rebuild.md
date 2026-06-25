# Full rebuild runbook - spot-worker-02

## Baseline

- Worker: spot-worker-02
- Role: utility/watcher
- GPU baseline: TITAN Xp 12GB + Quadro M4000 8GB
- Status: validated live

## Required models

- bge-m3:latest
- nomic-embed-text:latest
- phi3.5:latest

## Notes

Mount was manually restored and validated.

## Commands

Dry-run from spot-core: cd ~/spot-stack && provision/provision-worker.sh spot-worker-02
Apply from spot-core after OS/bootstrap recovery only: cd ~/spot-stack && provision/provision-worker.sh spot-worker-02 --apply
Validate from spot-core: ssh -o BatchMode=yes -o ConnectTimeout=8 spot-worker-02 'hostname; systemctl is-active ssh; systemctl is-active ollama; nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv,noheader; ollama list; findmnt /mnt/collective || true'

## Stop conditions

- Hostname mismatch.
- SSH inactive or unreachable.
- Ollama inactive.
- NVIDIA missing or wrong GPU.
- Required model missing after provision apply.
- /mnt/collective unavailable when required.
- W-06 apply attempted before restore_deferred is cleared.
