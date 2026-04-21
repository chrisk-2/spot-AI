Continuing Spot bridge work.

Run first:
- spot_save
- read /home/ogre/spot-stack/HANDOFF.md
- read /home/ogre/spot-stack/spot-core/STATE.md
- read /home/ogre/spot-stack/watch/spot-ops.sh
- read /home/ogre/spot-stack/watch/fleet-validate.sh
- read /home/ogre/spot-stack/spot-core/spotcore/app.py

Rules:
- no guessing
- read real runtime files before patching
- use runtime as source of truth
- fallback to GitHub only if runtime unavailable
- do not redesign system
- minimal changes only
- preserve auth and payload formats
- do not modify unrelated code
- enforce backup-first policy
- validate with the correct tool before restart

Current confirmed state:
- Stage 1 / Milestone A (Spot Core Trusted) is locked
- fleet-validate.sh passes in normal mode
- fleet-validate.sh --smoke passes
- spot-ops.sh now provides:
 - status
  - validate
  - validate-smoke
  - health
  - routing
  - audit
  - quarantine-state
  - quarantine
  - release
  - logs
- operator-facing Stage 2 v1 command surface is working
- spot-ops.sh status shows fleet health and routing audit summary cleanly
- spot-ops.sh quarantine-state exposes runtime eligibility/quarantine/degraded state
- current notable signal: spot-worker-03 fallback_count_window is nonzero while still healthy

Next task:
- extend spot-ops.sh with a remediation command
- summarize remediation-state.json in operator-friendly form
- expose:
  - worker
  - quarantined
  - degraded
  - degraded_reason
  - fallback_count_window
  - reason
  - last_updated_ts
