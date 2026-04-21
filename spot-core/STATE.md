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

Task:
- inspect current fleet-validate.sh
- identify duplicate/noisy checks
- clean validator output only
- preserve behavior unless required to fix broken validation
- then inspect app.py only for routing-audit write failure handling
- add explicit failure logging if needed
- run validation
- prepare checkpoint state
