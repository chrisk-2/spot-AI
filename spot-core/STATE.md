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
- routing correct for coding and heavy
- fallback verified working (coding + heavy)
- spottest operational

## Known Issues
- general routing incorrectly hitting worker-04 (heavy node)
- scheduler still allows cross-role scoring bleed

## Next Tasks
1. enforce strict role ownership (owned → fallback phases)
2. prevent general from ever landing on heavy unless explicitly allowed
3. extend fallback tests to full-chain validation (optional next)
