#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

cd "$ROOT"

echo "===== SPOT THINKING LOOP ====="
echo "timestamp=$(date -u -Is)"
echo "host=$(hostname)"
echo "mode=read_only_append_only_reasoning"
echo "approval_authority=false"
echo "execution_allowed=false"
echo "mutation_authority=false"

echo
echo "===== STAGE 1: SITUATION ASSESSMENT ====="

timeout 1200 \
  python3 \
  "$ROOT/watch/thinking/situation-assessment.py"

echo
echo "===== STAGE 2: DRIFT DETECTION ====="

timeout 180 \
  python3 \
  "$ROOT/watch/thinking/drift-detection.py"

echo
echo "===== STAGE 3: RISK ASSESSMENT ====="

timeout 180 \
  python3 \
  "$ROOT/watch/thinking/risk-assessment.py"

echo
echo "===== STAGE 4: OPERATIONAL REASONING ====="

timeout 180 \
  python3 \
  "$ROOT/watch/thinking/operational-reasoning.py"

echo
echo "===== THINKING STATUS ====="

python3 \
  "$ROOT/watch/thinking/thinking-status.py"

echo
echo "thinking_loop=COMPLETE"
echo "operational_mutation_performed=false"
echo "approval_authority=false"
echo "execution_allowed=false"
echo "mutation_authority=false"
