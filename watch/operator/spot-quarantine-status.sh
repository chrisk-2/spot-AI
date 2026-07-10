#!/usr/bin/env bash
set -Eeuo pipefail

BASE_URL="${SPOT_BASE_URL:-http://127.0.0.1:8787}"
STATE_DIR="${WATCH_STATE_DIR:-/home/ogre/spot-stack/watch/state}"
FLEET_STATUS_FILE="${FLEET_STATUS_FILE:-${STATE_DIR}/fleet-status.json}"
TIMEOUT="${SPOT_QUARANTINE_STATUS_TIMEOUT:-5}"

section() { printf '\n===== %s =====\n' "$*"; }

section "SPOT QUARANTINE STATUS"
echo "timestamp=$(date -Is)"
echo "mode=read_only"
echo "mutation_authority=false"

section "FLEET PING QUARANTINE VIEW"
fleet="$(curl -fsS --connect-timeout 3 --max-time "$TIMEOUT" "${BASE_URL}/fleet/ping" 2>/dev/null || true)"
if [ -n "$fleet" ]; then
  printf '%s\n' "$fleet" | jq 'to_entries | map({
    worker: .key,
    ok: (.value.ok // null),
    eligible: (.value.eligible // null),
    quarantined: (.value.quarantined // null),
    degraded: (.value.degraded // null),
    reason: (.value.reason // null),
    primary_role: (.value.primary_role // null)
  })' 2>/dev/null || printf '%s\n' "$fleet"
else
  echo "fleet_ping=unavailable"
fi

section "FLEET STATUS FILE QUARANTINE VIEW"
if [ -f "$FLEET_STATUS_FILE" ]; then
  jq '
    .hosts
    | if type == "object" then
        to_entries
        | map({
            host: .key,
            eligible: (.value.eligible // null),
            quarantined: (.value.quarantined // null),
            ssh_ok: (.value.ssh_ok // null),
            service_ok: (.value.service_ok // null),
            alerts: (.value.alerts // [])
          })
      else
        .
      end
  ' "$FLEET_STATUS_FILE" 2>/dev/null || cat "$FLEET_STATUS_FILE"
else
  echo "missing=${FLEET_STATUS_FILE}"
fi

section "QUARANTINE COMMAND BOUNDARY"
echo "read_only_status_command=true"
echo "temporary_smoke_command=./watch/operator/spot-operator.sh smoke"
echo "manual_quarantine_requires_policy=true"
echo "release_must_restore_eligible=true"
echo "no_restart_required_for_smoke=true"
