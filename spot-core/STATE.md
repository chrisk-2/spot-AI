Continuing Spot bridge work.

Run first:
- spot_save
- read /home/ogre/spot-stack/HANDOFF.md
- read /home/ogre/spot-stack/spot-core/STATE.md
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
- routing-audit write failure logging already exists in spot-core/spotcore/app.py
- fleet-validate.sh output was cleaned
- fleet-validate.sh passes in normal mode
- fleet-validate.sh --smoke passes
- smoke mode confirms quarantine=true/eligible=false and release back to quarantined=false/eligible=true without restart
- Stage 1 / Milestone A (Spot Core Trusted) is now the locked baseline

Next task:
- begin Stage 2 — Spot Operator Ready
- define the first operator-facing entry points
- standardize a small safe command set for:
  - fleet validation
  - routing state
  - quarantine state
  - recent routing audit
  - watch logs
