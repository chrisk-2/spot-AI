# SPOT HANDOFF (LOCKED)

## PURPOSE
This file defines rules and workflow.
It does NOT track state.

State lives in:
spot-core/STATE.md

---

## SOURCE OF TRUTH

1. Runtime files explicitly provided by the user with sed/cat
2. Current live runtime paths listed in this handoff and STATE.md
3. GitHub repo only as fallback when runtime file content is not yet provided

Do not guess paths.
Do not prefer repo over live runtime when live runtime content is available.

---

## READ ORDER (MANDATORY)

1. HANDOFF.md
2. spot-core/STATE.md

---

## RULES

- no guessing ever
- read real files before patching
- use live runtime as source of truth when provided; use GitHub only as fallback
- do not redesign system unless explicitly asked
- do not do ad hoc edits
- use scripted validation
- all code changes must be verified with python3 -m py_compile before restart
- runtime file paths provided in this handoff are accessible and must be read directly
- do not claim repo or filesystem is unavailable
- do not generate example endpoints or models before reading real code
- do not change request/response formats (including auth style)
- when a live runtime file path is already known, read it before proposing any code
- do not ask the user to paste files that exist at known runtime paths
- do not present generic route/model examples in place of live patching
- preserve the current auth mechanism exactly; do not substitute bearer auth or header auth unless explicitly asked
- endpoint names must match the current implementation exactly; do not shorten, rename, or normalize paths

---

## ROUTING OWNERSHIP (LOCKED)

- general -> spot-worker-01
- utility -> spot-worker-02
- coding  -> spot-worker-03
- heavy   -> spot-worker-04

Do not change.

---

## PATHS

Repo root:
- /home/ogre/spot-stack

Core:
- /home/ogre/spot-stack/spot-core/spotcore/app.py

Watch layer:
- /home/ogre/spot-stack/watch/fleet-watch.sh
- /home/ogre/spot-stack/watch/fleet-remediate.sh
- /home/ogre/spot-stack/watch/fleet-validate.sh
- /home/ogre/spot-stack/watch/spot-ops.sh

State:
- /home/ogre/spot-stack/spot-core/STATE.md

Active compose (must be verified, not assumed):
- /home/ogre/spot-stack/docker-compose.yml
- /home/ogre/spot-stack/spot-core/docker-compose.yml

Current admin endpoints (must be verified in app.py, not assumed):
- /admin/read-file
- /admin/write-file
- /admin/restart-service
- /admin/validate

---

## WORKFLOW

Before any change:
- read STATE.md
- identify files in scope
- read those files with sed/cat; use repo only if runtime not provided

Then:
- make minimal change
- validate using scripts

---

## HANDOFF PROCESS

When switching chats:

1. run:
   spot_save

2. update:
   STATE.md

3. start new chat with:

Continuing Spot bridge work.

Run first:
- spot_save
- read /home/ogre/spot-stack/HANDOFF.md
- read /home/ogre/spot-stack/spot-core/STATE.md
- read /home/ogre/spot-stack/spot-core/spotcore/app.py

Rules:
- no guessing
- read real runtime files before patching
- use live runtime as source of truth when provided
- use GitHub only as fallback
- do not redesign system
- make minimal changes only
- validate with py_compile and scripted checks
- do not ask the user to paste code blocks that already exist at known runtime paths
- do not provide generic example models first
- do not invent new routes or payload shapes
- do not change request/response formats, including auth style

Current core path:
- /home/ogre/spot-stack/spot-core/spotcore/app.py

Task:
- read STATE.md
- read /home/ogre/spot-stack/spot-core/spotcore/app.py
- identify actual /admin endpoints
- apply models to those exact endpoints only
- do not invent route names, payload fields, or auth flow
- continue exactly from current state

---

END HANDOFF
