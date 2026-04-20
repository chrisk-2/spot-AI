Continuing Spot fleet work.

Repo:
https://github.com/chrisk-2/spot-AI

Run first:
- spot_save
- read HANDOFF.md
- read spot-core/STATE.md

Rules:
- no guessing
- read real files before patching
- use repo/runtime as source of truth
- do not redesign system
- use scripted validation

Current state:
- enforcement wrapper is ACTIVE in spot-core/app.py
- quarantine + unquarantine fully enforced
- restart-service hook implemented and WORKING
- service remediation added to watch/fleet-remediate.sh
- restart via POST /actions/restart-service/{worker}/ollama

Verified:
- spot-core container can SSH to workers (key-based)
- restart endpoint works:
- POST /actions/restart-service/{worker}/ollama
- returns ok:true with:
- restart_returncode=0
- remote_after=active
- validated live on spot-worker-01
- backup + action logging confirmed

Infra fixes completed:
- openssh-client installed in container
- SSH keys copied into container at runtime (/host-ssh -> /root/.ssh)
- permissions corrected
- /mnt/collective mounted into container
- backup + logs writing correctly
- unique backup dirs using time.time_ns()

Worker-01:
- ollama now systemd-managed
- sudo NOPASSWD for restart/is-active configured

Paths:
- backups: /mnt/collective/backups
- logs: /mnt/collective/logs/spot/actions.jsonl

Current goal:
Add service remediation into fleet-remediate.sh using spot-core API

Target change:
- detect service-down condition (ollama)
- call:
  curl -s -X POST http://127.0.0.1:8787/actions/restart-service/{worker}/ollama
- DO NOT modify existing quarantine logic
- DO NOT redesign script

Scope:
- file: ~/spot-stack/watch/fleet-remediate.sh

Validation:
- stop ollama on worker
- ensure remediation triggers restart via API
- confirm backup + log entries created
- confirm service returns active

Note:

