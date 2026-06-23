#!/usr/bin/env bash
# spot-wake.sh — send WOL magic packet to any fleet node
# Usage: spot-wake.sh <hostname|all-workers|all-infra|all>
set -euo pipefail

LOG_FILE="${LOG_FILE:-/mnt/collective/logs/spot/wake.jsonl}"
mkdir -p "$(dirname "$LOG_FILE")" 2>/dev/null || true

log() {
  printf '{"ts":"%s","event":"%s","host":"%s","detail":"%s"}\n' \
    "$(date -u +'%Y-%m-%dT%H:%M:%SZ')" "$1" "$2" "${3:-}" | tee -a "$LOG_FILE" 2>/dev/null || true
}

# Full fleet MAC table — generated from starfleet-infra/inventory/nodes.json
declare -A MAC=(
  # Workers
  [spot-worker-01]="d8:43:ae:a9:c2:4c"
  [spot-worker-02]="d8:cb:8a:3e:94:fa"
  [spot-worker-03]="b4:2e:99:a5:17:ef"
  [spot-worker-04]="d8:43:ae:1f:88:2b"
  [spot-worker-05]="04:d4:c4:54:cd:6f"
  [spot-worker-06]="04:d4:c4:48:43:48"
  # Infrastructure
  [spot-core]="4c:cc:6a:be:97:47"
  [starfleet-core]="d8:9e:f3:7f:40:66"
  [dns-core]="f8:b4:6a:a4:2b:8d"
  [starfleet-tower]="00:e8:4c:68:5e:25"
  [unimatrix6]="00:11:32:f0:1d:75"
)

declare -A BROADCAST=(
  [spot-worker-01]="192.168.10.255"
  [spot-worker-02]="192.168.10.255"
  [spot-worker-03]="192.168.10.255"
  [spot-worker-04]="192.168.10.255"
  [spot-worker-05]="192.168.10.255"
  [spot-worker-06]="192.168.10.255"
  [spot-core]="192.168.60.255"
  [starfleet-core]="192.168.60.255"
  [dns-core]="192.168.60.255"
  [starfleet-tower]="192.168.30.255"
  [unimatrix6]="192.168.50.255"
)

WORKERS=(spot-worker-01 spot-worker-02 spot-worker-03 spot-worker-04 spot-worker-05 spot-worker-06)
INFRA=(spot-core starfleet-core dns-core starfleet-tower unimatrix6)

wake_host() {
  local host="$1"
  local mac="${MAC[$host]:-}"
  local bcast="${BROADCAST[$host]:-255.255.255.255}"

  if [[ -z "$mac" ]]; then
    echo "ERROR: No MAC for $host"
    log "wake_fail" "$host" "no_mac"
    return 1
  fi

  if ! command -v wakeonlan &>/dev/null; then
    echo "ERROR: wakeonlan not installed — sudo apt install wakeonlan"
    return 1
  fi

  echo "Waking $host ($mac) via $bcast..."
  log "wake_send" "$host" "mac=$mac bcast=$bcast"
  wakeonlan -i "$bcast" "$mac"
  log "wake_sent" "$host" "ok"
  echo "Magic packet sent to $host — allow 30-60s to boot"
}

TARGET="${1:-}"
case "$TARGET" in
  "")
    echo "Usage: $0 <hostname|all-workers|all-infra|all>" >&2
    echo "Hosts: ${!MAC[*]}" >&2
    exit 2
    ;;
  all-workers)
    for h in "${WORKERS[@]}"; do wake_host "$h" || true; done ;;
  all-infra)
    for h in "${INFRA[@]}"; do wake_host "$h" || true; done ;;
  all)
    for h in "${WORKERS[@]}" "${INFRA[@]}"; do wake_host "$h" || true; done ;;
  *)
    wake_host "$TARGET" ;;
esac
