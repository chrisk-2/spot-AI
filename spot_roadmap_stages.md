
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

---

# Operational Progress Addendum — 2026-07-18

This addendum supersedes earlier current-position statements in this roadmap.

## Current Seven-Step Build Position

1. Trusted Core — complete
2. Operator Surface — mostly complete
3. Senses — complete
4. Memory Foundation — complete
5. Thinking Loop — complete through Modules 42-46
6. Controlled Hands — not authorized
7. Operator Body/Face — later

## Thinking Loop Capability

Spot can now:

- assess the current fleet situation
- compare verified situation records for drift
- score operational risk deterministically
- generate governed advisory recommendations
- preserve the reasoning chain as verified append-only memory
- present a unified Thinking Loop status

The Thinking Loop cannot approve or execute its own recommendations.

Locked state:

- approval_authority=false
- execution_allowed=false
- mutation_authority=false
- Spot Core remains sole executor
