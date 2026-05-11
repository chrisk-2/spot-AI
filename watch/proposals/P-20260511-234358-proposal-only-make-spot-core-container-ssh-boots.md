# Spot Proposal P-20260511-234358-proposal-only-make-spot-core-container-ssh-boots

status: rejected  
rejected_utc: 20260511-234504
created_utc: 20260511-234358  
task: Proposal only: make Spot Core container SSH bootstrap durable. Root cause: docker-compose.yml mounts /home/ogre/.ssh to /host-ssh but startup copies id_ed25519 while fleet SSH uses spot_fleet. Runtime repair proved /root/.ssh/config with IdentityFile /root/.ssh/spot_fleet fixes /admin/read-file. Do not execute now. Target exact file only: docker-compose.yml. Proposed change: copy /host-ssh/spot_fleet to /root/.ssh/spot_fleet, copy /host-ssh/spot_fleet.pub if present, copy /host-ssh/known_hosts, chmod key files, and create /root/.ssh/config with Host * IdentityFile /root/.ssh/spot_fleet IdentitiesOnly yes UserKnownHostsFile /root/.ssh/known_hosts. Validation: docker compose config; docker compose up -d --force-recreate spot-core; docker exec spot-core ssh -o BatchMode=yes -o ConnectTimeout=5 ogre@192.168.10.10 'hostname && echo READ_OK'; curl /admin/read-file for spot-worker-01 /etc/os-release; spot validate. Rollback must be exact-file rollback: git restore docker-compose.yml.  
role: coding  
worker: spot-worker-03  
model: qwen2.5-coder:7b  
gpu: GTX 1070 8GB  

---

**SUMMARY**
- Ensure Spot Core container SSH bootstrap is durable.
- Propose changes to `docker-compose.yml` to copy necessary SSH keys and create configuration files.

**RISK_CLASS**
- Low. Changes are limited to Docker Compose file and basic SSH setup, which are well-documented and low-risk operations.

**FILES_AFFECTED**
- `/home/ogre/spot-stack/spot-core/docker-compose.yml`

**VALIDATION_COMMANDS**
- `docker compose config`
- `docker compose up -d --force-recreate spot-core`
- `docker exec spot-core ssh -o BatchMode=yes -o ConnectTimeout=5 ogre@192.168.10.10 'hostname && echo READ_OK'`
- `curl /admin/read-file for spot-worker-01 /etc/os-release`
- `spot validate`

**ROLLBACK**
- `git restore docker-compose.yml`

**NEXT_SAFE_ACTION**
- Ensure the proposed changes are committed and tested in a staging environment before deploying to production.
