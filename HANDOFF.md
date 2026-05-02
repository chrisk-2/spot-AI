# SPOT HANDOFF (LOCKED)

## PURPOSE

This file defines permanent rules, workflow, and runtime paths.
It does NOT track current state, active tasks, or next steps.

Current state lives in:

- /home/ogre/spot-stack/spot-core/STATE.md

Long-range phased integration plans live in:

- /home/ogre/spot-stack/HANDOFF-CODEX-INTEGRATION.md
- /home/ogre/spot-stack/HANDOFF-SPOT-INTEGRATION.md

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
4. /home/ogre/spot-stack/Spot_Autonomy_Policy 
5. integration handoff docs if task is architectural:
   - /home/ogre/spot-stack/HANDOFF-CODEX-INTEGRATION.md
   - /home/ogre/spot-stack/HANDOFF-SPOT-INTEGRATION.md


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

1. /home/ogre/spot-stack/HANDOFF.md
2. /home/ogre/spot-stack/spot-core/STATE.md
3. /home/ogre/spot-stack/ROADMAP.md
4. /home/ogre/spot-stack/Spot_Autonomy_Policy
5. integration handoff docs if task is architectural:
   - /home/ogre/spot-stack/HANDOFF-CODEX-INTEGRATION.md
   - /home/ogre/spot-stack/HANDOFF-SPOT-INTEGRATION.md


]Do not use HANDOFF.md as state tracking.
Do not put next-task details in HANDOFF.md.
Put current status, verified results, open issues, and next steps in STATE.md only.
Put phased long-range construction planning in ROADMAP.md only.
Put phased subsystem integration plans in dedicated HANDOFF-* docs.

---

## END HANDOFF

## 2026-05-02 — PHASE 1.7 Utility Latency Diagnostic Handoff

Current active lane: PHASE 1.7 — SUPERVISED APPLY-PLAN ENGINE.

Last known clean checkpoint before utility prompt patch attempt:
- Commit: c0de7dd checkpoint: 2026-05-02-03:56:21
- Diagnostic proposal/apply-plan/handoff created and verified:
  - P-20260502-035124-prepare-a-low-risk-diagnostic-only-plan-to-reduc
  - APPLY-P-20260502-035124-prepare-a-low-risk-diagnostic-only-plan-to-reduc
  - HANDOFF-APPLY-P-20260502-035124-prepare-a-low-risk-diagnostic-only-plan-to-reduc
- Handoff is non-mutating:
  - execution_allowed: false
  - mutation_allowed: false
  - risk_class: low
  - backup_required: true
  - backup_bound: false

Storage/backup baseline:
- /mnt/collective restored as CIFS mount to //unimatrix6/docker and persisted in /etc/fstab.
- Worker backup freshness reader now resolves timestamped worker-config metadata and ignores non-timestamp dirs such as probe.
- spot_save now reports worker backups OK:
  - spot-worker-01: OK last_backup=20260502T001701Z
  - spot-worker-02: OK last_backup=20260502T001701Z
  - spot-worker-03: OK last_backup=20260502T001701Z
  - spot-worker-04: OK last_backup=20260502T001701Z

Confirmed utility latency root cause:
- Raw worker-02 Ollama is fast: about 0.5s–1.5s for phi3.5 "reply with ok".
- Spot utility path is slow: observed 15s–45s for `spot ask --role utility "reply with ok"`.
- Root cause found in /home/ogre/spot-stack/watch/spot-client.sh:
  - `cmd_ask` always wraps ask prompts with `with_memory_prompt "$prompt"`.
  - `with_memory_prompt` injects Durable Memory Context into every `spot ask`.
  - This causes phi3.5 on worker-02 to produce long policy/memory responses instead of minimal answers.
- /home/ogre/spot-stack/spot-core/spotcore/app.py is not the injector; it forwards `req.prompt` to Ollama.

Current regression:
- Attempted patch to add `--memory` opt-in to `spot ask` failed:
  - error: `cmd_ask one-line anchor not found; inspect manually`
- Because the patch did not apply, old memory-injection behavior remains.
- Latest validation failed:
  - utility route timed out after 30002ms
  - [FAIL] utility route returned HTTP 503
  - RESULT: FAIL
- Do not continue feature work until utility ask prompt injection is fixed and fleet validation returns PASS.

Next recommended fix:
- Manually inspect and patch `cmd_ask` in watch/spot-client.sh.
- Desired behavior:
  - default `spot ask` sends the raw user prompt with no durable memory injection.
  - new `spot ask --memory` enables `with_memory_prompt`.
  - `spot propose` keeps durable memory injection unchanged.
- After patch:
  - `bash -n watch/spot-client.sh`
  - `time spot ask --role utility "reply with ok"`
  - `time spot ask --memory --role utility "reply with ok"`
  - `bash watch/fleet-validate.sh`
  - only save after validation is PASS.
