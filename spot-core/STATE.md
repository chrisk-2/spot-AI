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
- do not redesign system unless asked
- use scripted validation

Current status:
- enforcement wrapper is now implemented in spot-core/spotcore/app.py
- quarantine hook is enforced through:
  classify -> backup -> execute -> verify -> rollback path
- unquarantine hook is enforced through:
  classify -> backup -> execute -> verify -> rollback path
- real service mutation hook is now working:
  POST /actions/restart-service/{worker_name}/{service_name}
- verified successful restart of:
  spot-worker-01 / ollama
- backups and logs are writing to:
  /mnt/collective/backups
  /mnt/collective/logs/spot/actions.jsonl

Important implementation details now in place:
- unique backup dir naming uses time.time_ns()
- docker-compose.yml now mounts /mnt/collective into container
- docker-compose.yml also mounts host SSH material to /host-ssh and copies keys/known_hosts into /root/.ssh at container startup with corrected permissions
- spot-core container installs openssh-client at startup
- restart hook uses SSH from inside container successfully

Verified working behavior:
- docker compose exec spot-core ssh ogre@192.168.10.10 "echo ok" works
- curl -s -X POST "http://127.0.0.1:8787/actions/restart-service/spot-worker-01/ollama" | jq returns ok:true
- verification showed:
  restart_returncode=0
  remote_after=active

Worker-01 service control is now standardized enough for this path:
- ollama is controllable by systemd
- sudo NOPASSWD path for restart/is-active works

Next task:
Wire fleet-remediate.sh into spot-core so remediation uses the policy-enforced restart API instead of direct shell/SSH restart logic.

Files likely in scope:
- /home/ogre/spot-stack/watch/fleet-remediate.sh
- /home/ogre/spot-stack/spot-core/spotcore/app.py
- /home/ogre/spot-stack/docker-compose.yml
- /home/ogre/spot-stack/spot-core/STATE.md

Expected direction:
- replace direct restart action in fleet-remediate.sh with call to spot-core endpoint:
  POST /actions/restart-service/{worker}/{service}
- keep backup-first behavior and logging through spot-core as source of mutation control
- preserve existing remediation flow and avoid redesign
- validate with scripted test against a controlled ollama stop/restart scenario

Known separate issues:
- fleet routing validator still has unrelated routing failures from earlier work; do not confuse those with enforcement hook success
