# SPOT HANDOFF (LOCKED)

## PURPOSE

This file defines permanent rules, workflow, and runtime paths.
It does NOT track current state, active tasks, or next steps.

Current state lives in:

- /home/ogre/spot-stack/spot-core/STATE.md

---

## SOURCE OF TRUTH (STRICT ORDER)

1. Runtime files explicitly readable at known paths
2. Runtime paths defined in this file or STATE.md
3. GitHub repo ONLY as fallback:
   https://github.com/chrisk-2/spot-AI

Rules:

- NEVER prefer repo over runtime
- NEVER guess file contents
- If runtime path exists -> read it
- If runtime cannot be read -> fallback to repo
- If neither available -> STOP

---

## READ ORDER (MANDATORY)

1. /home/ogre/spot-stack/HANDOFF.md
2. /home/ogre/spot-stack/spot-core/STATE.md
3. /home/ogre/spot-stack/ROADMAP.md

---

## GLOBAL RULES (HARD LOCK)

- no guessing ever
- read real files before patching
- do not redesign system
- do not perform speculative fixes
- make minimal changes only
- do not expand scope
- do not “improve” unrelated code
- do not generate example routes/models before reading real code
- do not ask for files that exist at known runtime paths
- do not claim known runtime paths are unavailable
- endpoint names MUST match existing implementation exactly
- request/response formats MUST NOT change unless explicitly requested
- auth mechanism MUST remain exactly as implemented unless explicitly requested
- do not introduce new auth patterns
- validate with the correct tool for the file type:
  - Python: `python3 -m py_compile`
  - Shell: `bash -n`
  - JSON: `jq empty`

---

## POLICY LOCK (NON-NEGOTIABLE)

- NO BACKUP -> NO CHANGE
- preserve backup-first behavior
- do not weaken logging, verification, or rollback
- do not bypass enforcement wrappers
- all admin/mutating behavior must remain compliant

---

## ROUTING OWNERSHIP (LOCKED)

- general -> spot-worker-01
- utility -> spot-worker-02
- coding  -> spot-worker-03
- heavy   -> spot-worker-04

Do not change unless explicitly requested.

---

## PATHS (LIVE RUNTIME)

### Repo root
- /home/ogre/spot-stack

### Core
- /home/ogre/spot-stack/spot-core/spotcore/app.py
- /home/ogre/spot-stack/spot-core/spotcore/warmd.py
- /home/ogre/spot-stack/spot-core/config/cluster_config.json

### Watch layer
- /home/ogre/spot-stack/watch/fleet-watch.sh
- /home/ogre/spot-stack/watch/fleet-remediate.sh
- /home/ogre/spot-stack/watch/fleet-validate.sh
- /home/ogre/spot-stack/watch/fleet-monitor-snapshot.sh
- /home/ogre/spot-stack/watch/monitor-alert-state.sh
- /home/ogre/spot-stack/watch/spot-ops.sh
- /home/ogre/spot-stack/watch/spot-save.sh

### State
- /home/ogre/spot-stack/spot-core/STATE.md
- /home/ogre/spot-stack/watch/state/fleet-status.json
- /home/ogre/spot-stack/watch/state/remediation-state.json
- /home/ogre/spot-stack/watch/state/routing-audit.jsonl
- /home/ogre/spot-stack/watch/state/routing-audit-summary.json

### History / monitoring
- /home/ogre/spot-stack/watch/state/history/monitor-summary.jsonl
- /home/ogre/spot-stack/watch/state/history/monitor-alert-latest.json
- /home/ogre/spot-stack/watch/state/history/monitor-alert-transitions.jsonl
- /home/ogre/spot-stack/watch/state/history/snapshots

### Compose
- /home/ogre/spot-stack/docker-compose.yml

---

## WORKFLOW (MANDATORY)

### BEFORE ANY CHANGE

- read STATE.md
- identify exact files in scope
- read those files from runtime path

### THEN

- extract current behavior exactly from runtime
- confirm the exact implementation details relevant to the task

### ONLY THEN

- apply minimal patch to exact targets

### AFTER

- validate with the correct checker for the file type
- validate with existing scripts/endpoints where applicable
- save checkpoint only after verification

---

## SCOPE CONTROL (CRITICAL)

- ONLY modify explicitly requested files/routes/logic
- DO NOT touch unrelated code
- DO NOT fix unrelated bugs unless they block the requested task
- DO NOT refactor without being asked
- DO NOT restructure files without being asked

If something else is broken:
-> record it in STATE.md unless it blocks the current task

---

## ADMIN / MUTATION RULE

Mutating endpoints and control actions must always be discovered from live runtime `app.py`.

NEVER trust:

- previous chats
- handoff summaries
- assumed naming

ALWAYS read actual file.

When MCP work begins:

- wrap the current live control surface
- do not redesign the system first
- do not bypass policy/logging/verification/rollback
- do not invent cleaner route names until runtime behavior is fully mapped

---

## HANDOFF PROCESS (CHAT TO CHAT)

### Step 1
Run:

- `spot_save`

### Step 2
Update:

- /home/ogre/spot-stack/spot-core/STATE.md

### Step 3
Start new chat and read:

- /home/ogre/spot-stack/HANDOFF.md
- /home/ogre/spot-stack/spot-core/STATE.md

Do not use HANDOFF.md as state tracking.
Do not put next-task details in HANDOFF.md.
Put current status, verified results, open issues, and next steps in STATE.md only.
Put phased long-range construction planning in ROADMAP.md only.

---

## END HANDOFF
