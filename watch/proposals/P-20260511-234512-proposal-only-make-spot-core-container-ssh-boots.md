# Spot Proposal P-20260511-234512-proposal-only-make-spot-core-container-ssh-boots

status: approved  
approved_utc: 20260511-234551
created_utc: 20260511-234512  
task: Proposal only: make Spot Core container SSH bootstrap durable. Root cause: repo-root /home/ogre/spot-stack/docker-compose.yml mounts /home/ogre/.ssh to /host-ssh but startup copies id_ed25519 while fleet SSH uses spot_fleet. Runtime repair proved /root/.ssh/config with IdentityFile /root/.ssh/spot_fleet fixes /admin/read-file. Do not execute now. FILES_AFFECTED must contain exactly one file: /home/ogre/spot-stack/docker-compose.yml. Forbidden affected file: /home/ogre/spot-stack/spot-core/docker-compose.yml. Proposed change: copy /host-ssh/spot_fleet to /root/.ssh/spot_fleet, copy /host-ssh/spot_fleet.pub if present, copy /host-ssh/known_hosts, chmod key files, and create /root/.ssh/config with Host * IdentityFile /root/.ssh/spot_fleet IdentitiesOnly yes UserKnownHostsFile /root/.ssh/known_hosts. Validation commands must be: docker compose config; docker compose up -d --force-recreate spot-core; docker exec spot-core ssh -o BatchMode=yes -o ConnectTimeout=5 ogre@192.168.10.10 'hostname && echo READ_OK'; curl /admin/read-file for spot-worker-01 /etc/os-release; spot validate. Rollback must be exact-file rollback: git restore docker-compose.yml.  
role: coding  
worker: spot-worker-03  
model: qwen2.5-coder:7b  
gpu: GTX 1070 8GB  

---

**SUMMARY**
Make Spot Core container SSH bootstrap durable by ensuring the correct SSH keys and configuration are available.

**RISK_CLASS**
Low. This change affects only the SSH setup for Spot Core containers, which is less critical than network or service configurations.

**FILES_AFFECTED**
- /home/ogre/spot-stack/docker-compose.yml

**VALIDATION_COMMANDS**
1. docker compose config
2. docker compose up -d --force-recreate spot-core
3. docker exec spot-core ssh -o BatchMode=yes -o ConnectTimeout=5 ogre@192.168.10.10 'hostname && echo READ_OK'
4. curl /admin/read-file for spot-worker-01 /etc/os-release
5. spot validate

**ROLLBACK**
exact-file rollback: git restore docker-compose.yml

**NEXT_SAFE_ACTION**
Wait for the validation commands to pass before proceeding with a live implementation.
