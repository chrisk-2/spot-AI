# Spot Proposal P-20260515-manual-implement-command-path

status: approved  
approved_utc: 20260515-014748
created_utc: 20260515-manual
task: Implement approved Codex API patch proposal endpoint path as non-mutating command workflow.
role: coding
worker: manual-operator
model: none
gpu: none

---

SUMMARY
Add and validate the non-mutating implement command path that routes approved W-6 proposals to W-3 coding artifact generation.

RISK_CLASS
low

FILES_AFFECTED
/home/ogre/spot-stack/watch/spot-client.sh
/home/ogre/spot-stack/watch/spot-ops.sh

VALIDATION_COMMANDS
bash -n /home/ogre/spot-stack/watch/spot-client.sh
bash -n /home/ogre/spot-stack/watch/spot-ops.sh
spot validate

ROLLBACK
Use Spot Core pre-change backup/apply-plan rollback if this implementation proposal later becomes an approved apply plan.

NEXT_SAFE_ACTION
Operator review only.
