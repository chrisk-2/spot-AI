#!/usr/bin/env bash
set -euo pipefail

# Read-only presence oracle. Does not depend on UniFi.
# Override with: HOSTS="name=ip name=ip" ./watch/network/fleet-presence-oracle.sh

DEFAULT_HOSTS=(
  "opnsense=192.168.1.1"
  "dns-core=192.168.60.10"
  "unimatrix=192.168.50.10"
  "starfleet-tower=192.168.30.5"
)

if [[ -n "${HOSTS:-}" ]]; then
  read -r -a TARGETS <<< "$HOSTS"
else
  TARGETS=("${DEFAULT_HOSTS[@]}")
fi

probe_tcp() {
  local ip="$1"
  local port="$2"
  timeout 2 bash -c ":</dev/tcp/$ip/$port" >/dev/null 2>&1
}

printf '{\n'
printf '  "timestamp_utc": "%s",\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
printf '  "unifi_dependency": false,\n'
printf '  "hosts": [\n'

first=1
for pair in "${TARGETS[@]}"; do
  name="${pair%%=*}"
  ip="${pair#*=}"

  ping_ok=false
  if ping -c 1 -W 1 "$ip" >/dev/null 2>&1; then
    ping_ok=true
  fi

  tcp_ports=()
  case "$name" in
    dns-core) tcp_ports=(53) ;;
    unimatrix) tcp_ports=(2049 445) ;;
    starfleet-tower) tcp_ports=(80 443 2586) ;;
    opnsense) tcp_ports=(443 22) ;;
    *) tcp_ports=() ;;
  esac

  tcp_json=""
  for port in "${tcp_ports[@]}"; do
    ok=false
    if probe_tcp "$ip" "$port"; then ok=true; fi
    tcp_json="${tcp_json}${tcp_json:+, }\"$port\": $ok"
  done

  [[ "$first" -eq 0 ]] && printf ',\n'
  first=0
  printf '    {"name": "%s", "ip": "%s", "icmp": %s, "tcp": {%s}}' "$name" "$ip" "$ping_ok" "$tcp_json"
done

printf '\n  ],\n'

collective_ok=false
collective_type="absent"
if findmnt -rn /mnt/collective >/dev/null 2>&1; then
  collective_type="$(findmnt -rn -o FSTYPE /mnt/collective | head -1)"
  if timeout 3 stat /mnt/collective >/dev/null 2>&1; then
    collective_ok=true
  fi
fi

printf '  "nfs": {"mount": "/mnt/collective", "mounted": %s, "fstype": "%s"}\n' "$collective_ok" "$collective_type"
printf '}\n'
