#!/usr/bin/env bash
set -Eeuo pipefail

BASE_URL="${SPOT_BASE_URL:-http://127.0.0.1:8787}"
STATE_DIR="${WATCH_STATE_DIR:-/home/ogre/spot-stack/watch/state}"
SUMMARY_FILE="${ROUTING_AUDIT_SUMMARY_FILE:-${STATE_DIR}/routing-audit-summary.json}"
TIMEOUT="${SPOT_ROUTING_STATUS_TIMEOUT:-5}"

section() { printf '\n===== %s =====\n' "$*"; }

section "SPOT ROUTING STATUS"
echo "timestamp=$(date -Is)"
echo "mode=read_only"
echo "mutation_authority=false"
echo "base_url=${BASE_URL}"

section "ROUTING AUDIT API"
api="$(curl -fsS --connect-timeout 3 --max-time "$TIMEOUT" "${BASE_URL}/stats/routing-audit" 2>/dev/null || true)"
if [ -n "$api" ]; then
  printf '%s\n' "$api" | jq '{
    ok,
    window_count,
    primaries,
    fallbacks,
    violations,
    manual_overrides,
    last_violation_ts,
    role_owners,
    by_role
  }' 2>/dev/null || printf '%s\n' "$api"
else
  echo "api=unavailable"
fi

section "ROUTING AUDIT SUMMARY FILE"
if [ -f "$SUMMARY_FILE" ]; then
  jq '{
    ok,
    window_count,
    primaries,
    fallbacks,
    violations,
    manual_overrides,
    last_violation_ts,
    role_owners,
    by_role
  }' "$SUMMARY_FILE" 2>/dev/null || cat "$SUMMARY_FILE"
else
  echo "missing=${SUMMARY_FILE}"
fi

section "EXPECTED ROLE OWNERS"
cat <<MAP
general=spot-worker-01
utility=spot-worker-02
coding=spot-worker-03
heavy=spot-worker-04
review=spot-worker-05
reasoning=spot-worker-06
MAP

section "AUTHORITY"
echo "routing_change_authority=spot-core"
echo "worker_self_route_change=false"
echo "high_risk_network_change=false"
