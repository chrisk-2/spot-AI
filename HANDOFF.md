# SPOT HANDOFF (LOCKED)

## PURPOSE

This file defines rules and workflow.
It does NOT track state.

State lives in:

* /home/ogre/spot-stack/spot-core/STATE.md

---

## SOURCE OF TRUTH (STRICT ORDER)

1. Runtime files explicitly readable at known paths
2. Runtime paths defined in this file or STATE.md
3. GitHub repo ONLY as fallback:
   https://github.com/chrisk-2/spot-AI

Rules:

* NEVER prefer repo over runtime
* NEVER guess file contents
* If runtime path exists → read it
* If runtime cannot be read → fallback to repo
* If neither available → STOP

---

## READ ORDER (MANDATORY)

1. /home/ogre/spot-stack/HANDOFF.md
2. /home/ogre/spot-stack/spot-core/STATE.md

---

## GLOBAL RULES (HARD LOCK)

* no guessing ever
* read real files before patching
* do not redesign system
* do not perform speculative fixes
* make minimal changes only
* do not expand scope
* do not “improve” unrelated code
* do not generate example routes/models before reading real code
* do not ask user for files that exist at known runtime paths
* do not claim runtime paths are unavailable
* endpoint names MUST match existing implementation exactly
* request/response formats MUST NOT change
* auth mechanism MUST remain exactly as implemented
* do not introduce new auth patterns
* all changes must pass:
  python3 -m py_compile

---

## POLICY LOCK (NON-NEGOTIABLE)

* NO BACKUP → NO CHANGE
* preserve backup-first behavior
* do not weaken logging, verification, or rollback
* do not bypass enforcement wrappers
* all admin/mutating behavior must remain compliant

---

## ROUTING OWNERSHIP (LOCKED)

* general → spot-worker-01
* utility → spot-worker-02
* coding  → spot-worker-03
* heavy   → spot-worker-04

Do not change.

---

## PATHS (LIVE RUNTIME)

Repo root:

* /home/ogre/spot-stack

Core:

* /home/ogre/spot-stack/spot-core/spotcore/app.py

Watch layer:

* /home/ogre/spot-stack/watch/fleet-watch.sh
* /home/ogre/spot-stack/watch/fleet-remediate.sh
* /home/ogre/spot-stack/watch/fleet-validate.sh
* /home/ogre/spot-stack/watch/spot-ops.sh

State:

* /home/ogre/spot-stack/spot-core/STATE.md

Compose:

* /home/ogre/spot-stack/docker-compose.yml
* /home/ogre/spot-stack/spot-core/docker-compose.yml

---

## WORKFLOW (MANDATORY)

### BEFORE ANY CHANGE

* read STATE.md
* identify exact files in scope
* read those files from runtime path

### THEN

* extract current behavior EXACTLY
* confirm:

  1. endpoint names
  2. auth mechanism
  3. request payload structure

### ONLY THEN

* apply minimal patch to exact targets

### AFTER

* run python3 -m py_compile
* validate via scripts/endpoints

---

## SCOPE CONTROL (CRITICAL)

* ONLY modify explicitly requested endpoints
* DO NOT touch unrelated routes
* DO NOT fix unrelated bugs
* DO NOT refactor
* DO NOT restructure files

If something else is broken:
→ ignore it unless it blocks this task

---

## ADMIN ENDPOINT RULE

Admin endpoints must be discovered from app.py.

NEVER trust:

* previous chats
* handoff summaries
* assumed naming

ALWAYS read actual file.

---

## HANDOFF PROCESS (CHAT TO CHAT)

### Step 1

Run:

* spot_save

### Step 2

Update:

* /home/ogre/spot-stack/spot-core/STATE.md

### Step 3 (NEW CHAT START)

Paste:

---

Continuing Spot bridge work.

Run first:

* spot_save
* read /home/ogre/spot-stack/HANDOFF.md
* read /home/ogre/spot-stack/spot-core/STATE.md
* read /home/ogre/spot-stack/spot-core/spotcore/app.py

Rules:

* no guessing
* read real runtime files before patching
* use runtime as source of truth
* fallback to GitHub only if runtime unavailable
* do not redesign system
* minimal changes only
* preserve auth and payload formats
* do not invent endpoints or models
* do not modify unrelated code
* enforce backup-first policy
* validate with python3 -m py_compile before restart

Task:

* read app.py
* identify EXACT /admin endpoints
* identify EXACT auth mechanism
* identify EXACT request payload structure
* THEN apply Pydantic models to those endpoints only
* do not change behavior
* enforce structure only (422 on invalid input)

Fallback rule:
If /home/ogre/spot-stack/spot-core/spotcore/app.py cannot be read:

* read from https://github.com/chrisk-2/spot-AI
* use that file ONLY

If neither is available:

* STOP

Output BEFORE patch:

1. exact /admin endpoints
2. exact auth mechanism
3. exact request fields

Then patch.

---

## END HANDOFF
