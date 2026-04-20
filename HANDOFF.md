# SPOT HANDOFF (LOCKED)

## PURPOSE
This file defines rules and workflow.
It does NOT track state.

State lives in:
spot-core/STATE.md

---

## SOURCE OF TRUTH

1. Runtime files (when explicitly provided via sed/cat)
2. GitHub repo

Never assume filesystem access.

---

## READ ORDER (MANDATORY)

1. HANDOFF.md
2. spot-core/STATE.md

---

## RULES

- no guessing ever
- read real files before patching
- use runtime or repo as source of truth
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
- read those files with sed/cat or repo

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

Continuing Spot fleet work.

Repo:
https://github.com/chrisk-2/spot-AI

Run:
- spot_save
- read HANDOFF.md
- read STATE.md

Rules:
- no guessing
- read real files before patching
- use repo/runtime as source of truth

Task:
(read STATE.md and continue)

---

END HANDOFF
