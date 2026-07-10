#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
OPERATOR="${ROOT}/watch/operator/spot-operator.sh"

LOG_ROOT="${SPOT_NETWORK_SNAPSHOT_ROOT:-/mnt/collective/logs/spot/actions}"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
HOST="$(hostname -s)"
SNAPSHOT="${LOG_ROOT}/network-incident-${HOST}-${STAMP}-$$.log"

if [[ ! -d /mnt/collective ]]; then
  echo "ERROR: /mnt/collective is unavailable" >&2
  exit 1
fi

mkdir -p "$LOG_ROOT"

if [[ ! -w "$LOG_ROOT" ]]; then
  echo "ERROR: snapshot destination is not writable: $LOG_ROOT" >&2
  exit 1
fi

umask 027
set -o noclobber

{
  echo "=== SPOT NETWORK INCIDENT SNAPSHOT ==="
  echo "timestamp_utc: $(date -u -Is)"
  echo "snapshot_id: network-incident-${HOST}-${STAMP}-$$"
  echo "observer: ${HOST}"
  echo "classification: diagnostic"
  echo "risk_class: observe-only"
  echo "mutation_authority: false"
  echo "network_configuration_modified: false"
  echo

  echo "===== NETWORK HEALTH SUMMARY ====="
  timeout 60 "$OPERATOR" network-health-summary 2>&1 || true
  echo

  echo "===== CRITICAL HOSTS ====="
  timeout 60 "$OPERATOR" critical-hosts 2>&1 || true
  echo

  echo "===== PROXY / TUNNEL HEALTH ====="
  timeout 60 "$OPERATOR" proxy-tunnel-health 2>&1 || true
  echo

  echo "===== ADDRESSES ====="
  ip -brief address 2>&1 || true
  echo

  echo "===== ROUTES ====="
  ip route show 2>&1 || true
  echo

  echo "===== DNS ====="
  resolvectl status 2>&1 || cat /etc/resolv.conf 2>&1 || true
  echo

  echo "===== LISTENING TCP PORTS ====="
  ss -lntp 2>&1 || true
  echo

  echo "===== RECENT FAILED SERVICES ====="
  systemctl --failed --no-pager 2>&1 || true
  echo

  echo "===== RECENT CADDY / CLOUDFLARED LOGS ====="
  journalctl \
    -u caddy.service \
    -u cloudflared.service \
    --since '-15 minutes' \
    --no-pager \
    -n 200 2>&1 || true
  echo

  echo "final_outcome: snapshot_created"
} >"$SNAPSHOT"

set +o noclobber

sha256sum "$SNAPSHOT" >"${SNAPSHOT}.sha256"

echo "snapshot: $SNAPSHOT"
echo "checksum: ${SNAPSHOT}.sha256"
echo "mode: diagnostic-write-only"
echo "existing_artifacts_modified: false"
echo "network_configuration_modified: false"
