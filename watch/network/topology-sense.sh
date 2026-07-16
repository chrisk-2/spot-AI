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
  "spot-core:control-plane"
  "starfleet-tower:operations"
  "spot-ui-01:operator-ui"
  "spot-worker-01:general"
  "spot-worker-02:utility"
  "spot-worker-03:coding"
  "spot-worker-04:heavy"
  "spot-worker-05:review"
  "spot-worker-06:reasoning"
  "unimatrix6:storage"
  "starfleet-core:dns-secondary"
  "dns-core:dns-primary"
  "starfleet-edge-01:recovery-edge"
)

resolve_ipv4() {
  local host="$1"

  if [[ "$host" == "$(hostname -s)" || "$host" == "spot-core" ]]; then
    hostname -I 2>/dev/null |
      tr ' ' '\n' |
      awk '$1 ~ /^[0-9]+\./ && $1 !~ /^127\./ && $1 !~ /^172\./ {print; exit}'
    return
  fi

  local address

  address="$(
    getent ahostsv4 "$host" 2>/dev/null |
      awk '$1 !~ /^127\./ {print $1; exit}'
  )"

  if [[ -z "$address" ]]; then
    address="$(registry_ipv4 "$host")"
  fi

  printf '%s\n' "$address"
}

subnet_from_ipv4() {
  local address="$1"

  awk -F. '
    NF == 4 {
      printf "%s.%s.%s.0/24", $1, $2, $3
    }
  ' <<<"$address"
}

echo "===== SPOT FLEET TOPOLOGY SENSE ====="
echo "timestamp=$(date -Is)"
echo "observer=$(hostname)"
echo "mode=read_only"
echo "mutation_authority=false"
echo

echo "===== LOCAL INTERFACES ====="
ip -brief -4 address
echo

echo "===== LOCAL ROUTING ====="
ip -4 route show
echo

echo "===== DEFAULT GATEWAY ====="
default_gateway="$(
  ip -4 route show default |
    awk 'NR == 1 {print $3}'
)"
echo "default_gateway=${default_gateway:-UNKNOWN}"
echo

echo "===== DNS AUTHORITIES ====="

if command -v resolvectl >/dev/null 2>&1; then
  mapfile -t dns_servers < <(
    resolvectl dns 2>/dev/null |
      awk -F: '
        {
          for (i = 2; i <= NF; i++) {
            n = split($i, parts, /[[:space:]]+/)
            for (j = 1; j <= n; j++) {
              if (parts[j] ~ /^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$/) {
                print parts[j]
              }
            }
          }
        }
      ' |
      sort -u
  )

  mapfile -t dns_domains < <(
    resolvectl domain 2>/dev/null |
      awk -F: '
        {
          for (i = 2; i <= NF; i++) {
            gsub(/^[[:space:]]+|[[:space:]]+$/, "", $i)
            if ($i != "") print $i
          }
        }
      ' |
      sort -u
  )
else
  mapfile -t dns_servers < <(
    awk '/^nameserver / {print $2}' /etc/resolv.conf |
      sort -u
  )
  dns_domains=()
fi

if (( ${#dns_servers[@]} == 0 )); then
  echo "dns_server=UNKNOWN"
else
  printf 'dns_server=%s\n' "${dns_servers[@]}"
fi

if (( ${#dns_domains[@]} == 0 )); then
  echo "dns_domain=UNKNOWN"
else
  printf 'dns_domain=%s\n' "${dns_domains[@]}"
fi

echo
echo "===== RESOLVED FLEET PLACEMENT ====="

printf '%-23s %-18s %-16s %-18s\n' \
  "HOST" "ROLE" "ADDRESS" "SUBNET"

printf '%-23s %-18s %-16s %-18s\n' \
  "-----------------------" \
  "------------------" \
  "----------------" \
  "------------------"

resolved=0
unresolved=0

for item in "${HOSTS[@]}"; do
  host="${item%%:*}"
  role="${item#*:}"
  address="$(resolve_ipv4 "$host")"

  if [[ -z "$address" ]]; then
    printf '%-23s %-18s %-16s %-18s\n' \
      "$host" "$role" "UNRESOLVED" "UNKNOWN"
    unresolved=$((unresolved + 1))
    continue
  fi

  subnet="$(subnet_from_ipv4 "$address")"

  printf '%-23s %-18s %-16s %-18s\n' \
    "$host" "$role" "$address" "$subnet"

  resolved=$((resolved + 1))
done

echo
echo "===== OBSERVED SUBNETS ====="

{
  ip -4 route show |
    awk '$1 ~ /^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+\// {print $1}'

  for item in "${HOSTS[@]}"; do
    host="${item%%:*}"
    address="$(resolve_ipv4 "$host")"
    [[ -n "$address" ]] && subnet_from_ipv4 "$address"
  done
} |
  sort -Vu |
  sed 's/^/subnet=/'

echo
echo "summary_hosts=${#HOSTS[@]}"
echo "summary_resolved=${resolved}"
echo "summary_unresolved=${unresolved}"

if (( unresolved == 0 )); then
  echo "overall=COMPLETE"
else
  echo "overall=PARTIAL"
fi

echo "network_configuration_modified=false"
echo "mutation_performed=false"
