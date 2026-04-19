# SPOT STATE

Continuing Spot fleet work.

Repo:
https://github.com/chrisk-2/spot-AI

Current state:
- spot-core running in Docker on :8787
- fleet registration working
- /fleet and /fleet/ping working
- workers healthy and reachable via Ollama
- system stable after restart (re-registration required)

Fleet:
- spot-worker-01 → general (192.168.10.10)
- spot-worker-02 → utility (192.168.10.11)
- spot-worker-03 → coding (192.168.10.13)
- spot-worker-04 → heavy (192.168.10.14)

Key rule:
- NO BACKUP = NO CHANGE (autonomy policy locked)

Docs:
- Autonomy policy finalized
- Roadmap stages defined

Files to reference:
- Autonomy policy: :contentReference[oaicite:0]{index=0}
- Roadmap: :contentReference[oaicite:1]{index=1}
- Worker specs:
  - worker-01: :contentReference[oaicite:2]{index=2}
  - worker-02: :contentReference[oaicite:3]{index=3}
  - worker-03: :contentReference[oaicite:4]{index=4}
  - worker-04: :contentReference[oaicite:5]{index=5}

Rules:
- no guessing
- read real code before modifying
- do not redesign architecture
- enforce autonomy policy in code (not just docs)

Current phase:
Stage 1 — Spot Core completion (late phase)

Next goal:
Wire autonomy enforcement into spot-core:
1. risk classification
2. backup gate (/mnt/collective/backups)
3. execution wrapper (log + verify + rollback)

Constraints:
- fleet currently re-registers on restart (stateless)
- do not introduce persistence redesign unless asked

Success criteria:
- every mutating action forced through:
  classify → backup → execute → verify → rollback if needed
- backup path logged before execution
- failure blocks execution cleanly

Task:
Start implementing enforcement hooks in spot-core/app.py
