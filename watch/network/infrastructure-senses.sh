#!/usr/bin/env bash
set -u

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
OPERATOR="${ROOT}/watch/operator/spot-operator.sh"

CHECKS=(
  resource-sense
  mount-sense
  worker-runtime-sense
  certificate-sense
)

completed=0
warn=0

echo "===== SPOT INFRASTRUCTURE SENSES ====="
echo "timestamp=$(date -Is)"
echo "host=$(hostname)"
echo "mode=read_only"
echo "mutation_authority=false"
echo

for check in "${CHECKS[@]}"; do
  echo "######## ${check} ########"

  if timeout 180 "$OPERATOR" "$check"; then
    echo "command_status=PASS"
    completed=$((completed + 1))
  else
    rc=$?
    echo "command_status=WARN"
    echo "command_exit=${rc}"
    warn=$((warn + 1))
  fi

  echo
done

echo "summary_completed=${completed}"
echo "summary_warn=${warn}"

if (( warn == 0 )); then
  echo "overall=COMPLETE"
else
  echo "overall=DEGRADED"
fi

echo "mutation_performed=false"
