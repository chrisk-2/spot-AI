# Spot Proposal P-20260502-020447-investigate-and-prepare-a-safe-remediation-plan-

status: pending_review  
created_utc: 20260502-020447  
task: Investigate and prepare a safe remediation plan for current validation issues: worker backup freshness metadata missing under /mnt/collective/backups/spot-worker-*/worker-config/latest/metadata.json, and intermittent worker-02 utility route HTTP 503 / high latency. Do not mutate files or services. Include exact diagnostics, backup requirements, validation commands, and rollback plan.  
role: coding  
worker: spot-worker-03  
model: qwen2.5-coder:7b  
gpu: GTX 1070 8GB  

---

**SUMMARY**
The current Spot stack is reporting intermittent HTTP 503 errors on the worker-02 node, along with missing backup freshness metadata. A safe remediation plan will be prepared to address these issues without mutating files or services.

**RISK_CLASS**
High - There are risks of increased downtime and data loss due to missing backup metadata and potential service disruptions.

**FILES_AFFECTED**
- /mnt/collective/backups/spot-worker-*/worker-config/latest/metadata.json

**VALIDATION_COMMANDS**
1. spot validate
2. python3 -m json.tool /home/ogre/spot-stack/spot-core/config/cluster_config.json >/dev/null
3. spot ask "show worker latency"
4. spot ask "what is the current fleet status"

**ROLLBACK**
1. Restore the missing metadata.json file from a backup taken before the issue began.
2. Revert any changes made to cluster configuration files during this proposal.

**NEXT_SAFE_ACTION**
- Retrieve and inspect existing backups of /mnt/collective/backups/spot-worker-*/worker-config/latest/metadata.json.
- Confirm that the backup is up-to-date and does not contain the missing metadata.
- If a suitable backup exists, proceed with restoring it to the affected node.
- After restoration, validate the system status using the provided validation commands.
