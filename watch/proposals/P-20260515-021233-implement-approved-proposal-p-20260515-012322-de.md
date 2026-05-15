# Spot Proposal P-20260515-021233-implement-approved-proposal-p-20260515-012322-de

status: approved
approved_utc: 20260515-021825
created_utc: 20260515-021233  
task: Implement approved proposal P-20260515-012322-design-codex-api-patch-proposal-endpoint-no-muta as a non-mutating coding artifact.  
role: coding  
worker: spot-worker-03  
model: qwen2.5-coder:7b  
gpu: GTX 1070 8GB  

---

SUMMARY
Refine the implement command path in spot-client.sh and spot-ops.sh to ensure it aligns with the approved W-6 reasoning proposal.

RISK_CLASS
low

FILES_AFFECTED
/home/ogre/spot-stack/watch/spot-client.sh
/home/ogre/spot-stack/watch/spot-ops.sh

VALIDATION_COMMANDS
bash -n /home/ogre/spot-stack/watch/spot-client.sh
bash -n /home/ogre/spot-stack/watch/spot-ops.sh
grep cmd_implement /home/ogre/spot-stack/watch/spot-client.sh
grep implement /home/ogre/spot-stack/watch/spot-client.sh
grep implement /home/ogre/spot-stack/watch/spot-ops.sh
spot validate

ROLLBACK
No rollback required; proposal-only artifact.

NEXT_SAFE_ACTION
Operator review only.
