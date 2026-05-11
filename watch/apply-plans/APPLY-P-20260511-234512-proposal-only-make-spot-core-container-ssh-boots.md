# Spot Apply Plan APPLY-P-20260511-234512-proposal-only-make-spot-core-container-ssh-boots

linked_proposal: P-20260511-234512-proposal-only-make-spot-core-container-ssh-boots
approved_utc: 20260511-234551
generated_utc: 20260511-234552
task: Proposal only: make Spot Core container SSH bootstrap durable. Root cause: repo-root /home/ogre/spot-stack/docker-compose.yml mounts /home/ogre/.ssh to /host-ssh but startup copies id_ed25519 while fleet SSH uses spot_fleet. Runtime repair proved /root/.ssh/config with IdentityFile /root/.ssh/spot_fleet fixes /admin/read-file. Do not execute now. FILES_AFFECTED must contain exactly one file: /home/ogre/spot-stack/docker-compose.yml. Forbidden affected file: /home/ogre/spot-stack/spot-core/docker-compose.yml. Proposed change: copy /host-ssh/spot_fleet to /root/.ssh/spot_fleet, copy /host-ssh/spot_fleet.pub if present, copy /host-ssh/known_hosts, chmod key files, and create /root/.ssh/config with Host * IdentityFile /root/.ssh/spot_fleet IdentitiesOnly yes UserKnownHostsFile /root/.ssh/known_hosts. Validation commands must be: docker compose config; docker compose up -d --force-recreate spot-core; docker exec spot-core ssh -o BatchMode=yes -o ConnectTimeout=5 ogre@192.168.10.10 'hostname && echo READ_OK'; curl /admin/read-file for spot-worker-01 /etc/os-release; spot validate. Rollback must be exact-file rollback: git restore docker-compose.yml.
risk_class: low
apply_status: pending_manual_review
mutation_allowed: false
backup_required: true
backup_bound: false
backup_artifact: pending
policy_class: supervised_apply_plan
autonomy_level: 1
execution_wrapper_required: true
executor: spot-core-controlled-wrapper
approval_gate: human_review_required
rollback_required: true
rollback_authority: recorded_prechange_backup_only

---

TARGET_FILES
- /home/ogre/spot-stack/docker-compose.yml

PRECHANGE_BACKUP_REQUIREMENTS
- Before any future mutation, Spot Core must create and verify a pre-change backup on Unimatrix.
- Required backup root: /mnt/collective/backups/<target>/<service>/<timestamp>/
- Backup path must be recorded in the action log before execution begins.
- If backup creation or verification fails, execution remains blocked.

PRECHECK_VALIDATION
- 1. docker compose config
- 2. docker compose up -d --force-recreate spot-core
- 3. docker exec spot-core ssh -o BatchMode=yes -o ConnectTimeout=5 ogre@192.168.10.10 'hostname && echo READ_OK'
- 4. curl /admin/read-file for spot-worker-01 /etc/os-release
- 5. spot validate

PLANNED_MUTATIONS
- Make Spot Core container SSH bootstrap durable by ensuring the correct SSH keys and configuration are available.
- This apply plan does not execute mutations.
- Future execution must route through Spot Core policy/enforcement wrappers.

POST_APPLY_VALIDATION
- 1. docker compose config
- 2. docker compose up -d --force-recreate spot-core
- 3. docker exec spot-core ssh -o BatchMode=yes -o ConnectTimeout=5 ogre@192.168.10.10 'hostname && echo READ_OK'
- 4. curl /admin/read-file for spot-worker-01 /etc/os-release
- 5. spot validate

ROLLBACK_PLAN
- exact-file rollback: git restore docker-compose.yml
- Rollback must use the recorded pre-change backup artifact.
- Rollback must be validated with the same post-apply validation commands.

HUMAN_REVIEW_GATE
- Confirm proposal is still approved and matches current runtime state.
- Confirm target files still exist and match expected live paths.
- Confirm risk class is correct under Spot Autonomy Policy.
- Confirm backup, validation, and rollback instructions are sufficient before any mutation.

NOTES
- Generated artifact is non-mutating.
- Memory and proposal history inform context but do not authorize execution.
- No high-risk network/firewall/DNS/DHCP/VLAN/routing mutation is authorized by this artifact.
