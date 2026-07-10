#!/usr/bin/env bash
set -u

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
OPERATOR="${ROOT}/watch/operator/spot-operator.sh"

CHECKS=(
  "dns-sense"
  "gateway-sense"
  "service-sense"
)

pass=0
warn=0

echo "=== SPOT NETWORK HEALTH SUMMARY ==="
echo "timestamp: $(date -Is)"
echo "host: $(hostname)"
echo

for check in "${CHECKS[@]}"; do
  tmp="$(mktemp)"

  echo "[$check]"

  if timeout 30 "$OPERATOR" "$check" >"$tmp" 2>&1; then
    echo "status: PASS"
    pass=$((pass + 1))
  else
    rc=$?
    echo "status: WARN"
    echo "exit_code: $rc"
    warn=$((warn + 1))
  fi

  sed -n '1,20p' "$tmp"
  echo
  rm -f "$tmp"
done

if (( warn == 0 )); then
  overall="HEALTHY"
else
  overall="DEGRADED"
fi

echo "summary: pass=${pass} warn=${warn}"
echo "overall: ${overall}"
echo "mode: read-only"
echo "mutation_performed: false"
