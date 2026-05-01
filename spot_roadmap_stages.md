
## D.4a Next Stage: Supervised Apply-Plan Engine

Objective:
- Convert approved proposals and generated patch artifacts into exact human-reviewable apply plans.

Required by policy:
- Follow Spot Autonomy Policy and Safety Model.
- No backup, no change.
- Use Unimatrix for verified pre-change backups and audit artifacts.

Scope:
- First target: approved utility fallback routing proposal.
- Intended config change: utility remains primary on worker-02, with worker-01 as fallback.
- Target file: /home/ogre/spot-stack/spot-core/config/cluster_config.json

Must include:
- exact target file
- exact before/after JSON block
- backup command/artifact path
- validation commands
- rollback instructions
- no automatic mutation until execution wrapper exists
