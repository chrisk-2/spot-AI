# SPOT FLEET STATE

## Architecture
- spot-core scheduler: :8787
- workers:
  - spot-worker-01 → general + fallback
  - spot-worker-02 → utility
  - spot-worker-03 → coding primary
  - spot-worker-04 → heavy primary

## Routing Policy
STRICT ROLE OWNERSHIP

general → worker-01
coding  → worker-03
heavy   → worker-04
utility → worker-02

Fallback:
coding → worker-01
heavy  → worker-01
general → NONE (fail if worker-01 down)

## Models
worker-01:
  - llama3.1:8b
  - mistral:7b
  - qwen2.5-coder:7b
  - qwen2.5:14b

worker-03:
  - qwen2.5-coder:7b
  - qwen2.5:14b

worker-04:
  - qwen2.5:14b

## Current Status
- routing: ✅ correct
- fallback: ✅ correct
- test harness: ✅ spottest working

## Known Issues
- general sometimes routes to worker-04 (needs strict enforcement)
- scheduler still allows cross-role scoring

## Next Tasks
1. enforce strict role ownership in scheduler
2. split owned vs fallback routing phases
3. extend fallback tests (full chain)

