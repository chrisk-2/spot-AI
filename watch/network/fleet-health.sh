#!/usr/bin/env bash
set -u

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
OPERATOR="${ROOT}/watch/operator/spot-operator.sh"

CHECKS=(
  "network-health-summary"
  "critical-hosts"
  "infrastructure-senses"
  "topology-sense"
  "ai-runtime-sense"
  "governance-sense"
)

completed=0
failed=0

echo "===== SPOT FLEET HEALTH ROLLUP ====="
echo "timestamp=$(date -Is)"
echo "host=$(hostname)"
echo "mode=read_only"
echo "mutation_authority=false"
echo

for check in "${CHECKS[@]}"; do
  tmp="$(mktemp)"

  echo "######## ${check} ########"

  if timeout 300 "$OPERATOR" "$check" >"$tmp" 2>&1; then
    echo "command_status=PASS"
    completed=$((completed + 1))
  else
    rc=$?
    echo "command_status=WARN"
    echo "command_exit=${rc}"
    failed=$((failed + 1))
  fi

  sed -n '1,80p' "$tmp"
  rm -f "$tmp"
  echo
done

echo "summary_checks=${#CHECKS[@]}"
echo "summary_completed=${completed}"
echo "summary_failed=${failed}"

if (( failed == 0 )); then
  echo "overall=COMPLETE"
else
  echo "overall=DEGRADED"
fi

echo "mutation_performed=false"
