# Spot Proposal P-20260501-133615-revise-routing-so-utility-role-remains-primary-o

status: approved
approved_utc: 20260501-133818
created_utc: 20260501-133615  
task: revise routing so utility role remains primary on worker-02 but has worker-01 as fallback in /home/ogre/spot-stack/spot-core/config/cluster_config.json; do not change spot-client.sh  
role: coding  
worker: spot-worker-03  
model: qwen2.5-coder:7b  
gpu: GTX 1070 8GB  

---

SUMMARY
- Revise the routing configuration to ensure that worker-02 continues to remain the primary for the utility role while using worker-01 as a fallback.
- No changes will be made to `spot-client.sh`.

RISK_CLASS
- Low risk. The change involves updating routing settings, which is a controlled operation affecting specific roles.

FILES_AFFECTED
- `/home/ogre/spot-stack/spot-core/config/cluster_config.json`

VALIDATION_COMMANDS
- spot ask "show current routing audit"

ROLLBACK
- To rollback to the previous state, apply the backup of `cluster_config.json` created before the change was made.

NEXT_SAFE_ACTION
- Run the validation command to confirm that the changes have been applied correctly and verify that worker-02 remains primary with worker-01 as a fallback.
