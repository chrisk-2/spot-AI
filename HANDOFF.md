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

4. Do not ask the user to paste code blocks that already exist at known runtime paths.
Read the live runtime file paths listed in this handoff first.

Continuing Spot bridge work.

Run first:
- spot_save
- read /home/ogre/spot-stack/HANDOFF.md
- read /home/ogre/spot-stack/spot-core/STATE.md

Rules:
- no guessing
- read real runtime files before patching
- use live runtime as source of truth when provided
- use GitHub only as fallback
- do not redesign system
- make minimal changes only
- validate with py_compile and scripted checks

Current core path:
- /home/ogre/spot-stack/spot-core/spotcore/app.py

Task:
- read STATE.md
- read the file(s) in scope
- continue exactly from current state
- Do not provide generic example models first.
Read the current /admin handlers in /home/ogre/spot-stack/spot-core/spotcore/app.py, then patch the live shapes only.

---

END HANDOFF
