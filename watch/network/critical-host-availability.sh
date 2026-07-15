#!/usr/bin/env bash
set -u

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
HOST_REGISTRY="${ROOT}/spot-core/config/host_registry.json"

registry_ipv4() {
  local host="$1"

  [[ -f "$HOST_REGISTRY" ]] || return 0
  command -v jq >/dev/null 2>&1 || return 0

  jq -r     --arg host "$host"     '.hosts[]? | select(.name == $host) | .ip // empty'     "$HOST_REGISTRY" 2>/dev/null |
    head -n1
}

HOSTS=(
  spot-core
  starfleet-tower
  spot-ui-01
  spot-worker-01
  spot-worker-02
  spot-worker-03
  spot-worker-04
  spot-worker-05
  spot-worker-06
  unimatrix6
  starfleet-core
  dns-core
  spot-edge-01
)

resolved=0
reachable=0
ssh_open=0
warn=0

echo "=== SPOT CRITICAL HOST AVAILABILITY ==="
echo "timestamp: $(date -Is)"
echo "observer: $(hostname)"
echo
printf '%-23s %-16s %-10s %-10s\n' \
  "HOST" "ADDRESS" "ICMP" "SSH"
printf '%-23s %-16s %-10s %-10s\n' \
  "-----------------------" "----------------" "----------" "----------"

for host in "${HOSTS[@]}"; do
  address="$(getent ahostsv4 "$host" 2>/dev/null | awk 'NR == 1 {print $1}')"

  if [[ -z "$address" ]]; then
    address="$(registry_ipv4 "$host")"
  fi

  if [[ -z "$address" ]]; then
    printf '%-23s %-16s %-10s %-10s\n' \
      "$host" "UNRESOLVED" "UNKNOWN" "UNKNOWN"
    warn=$((warn + 1))
    continue
  fi

  resolved=$((resolved + 1))

  if ping -c 1 -W 1 "$address" >/dev/null 2>&1; then
    icmp="PASS"
    reachable=$((reachable + 1))
  else
    icmp="WARN"
    warn=$((warn + 1))
  fi

  if timeout 2 bash -c \
    "exec 3<>/dev/tcp/${address}/22" >/dev/null 2>&1; then
    ssh="OPEN"
    ssh_open=$((ssh_open + 1))
  else
    ssh="CLOSED"
    warn=$((warn + 1))
  fi

  printf '%-23s %-16s %-10s %-10s\n' \
    "$host" "$address" "$icmp" "$ssh"
done

echo
echo "summary:"
echo "  configured_hosts=${#HOSTS[@]}"
echo "  resolved=${resolved}"
echo "  icmp_reachable=${reachable}"
echo "  ssh_open=${ssh_open}"
echo "  observations=${warn}"

if (( warn == 0 )); then
  echo "overall: HEALTHY"
else
  echo "overall: DEGRADED"
fi

echo "mode: read-only"
echo "mutation_performed: false"
