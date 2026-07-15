#!/usr/bin/env bash
set -Eeuo pipefail

TIMEOUT="${SPOT_DNS_SENSE_TIMEOUT:-3}"

section() { printf '\n===== %s =====\n' "$*"; }

section "SPOT DNS SENSE"
echo "timestamp=$(date -Is)"
echo "host=$(hostname)"
echo "mode=read_only"
echo "mutation_authority=false"

section "RESOLVER STATE"
resolvectl status 2>/dev/null || cat /etc/resolv.conf 2>/dev/null || true

section "CRITICAL NAME LOOKUPS"
for h in \
  spot-core \
  spot-worker-01 \
  spot-worker-02 \
  spot-worker-03 \
  spot-worker-04 \
  spot-worker-05 \
  spot-worker-06 \
  unimatrix6 \
  starfleet-core \
  dns-core \
  spot-edge-01 \
  spot.starfleetcore.com
do
  echo "--- $h ---"
  getent hosts "$h" || true
  timeout "$TIMEOUT" resolvectl query "$h" 2>/dev/null || true
done

section "DNS SERVER REACHABILITY"
servers="$(resolvectl dns 2>/dev/null | awk '{for (i=3;i<=NF;i++) print $i}' | sort -u || true)"
if [ -z "$servers" ]; then
  servers="192.168.60.10 192.168.60.20 192.168.10.1"
fi

for s in $servers; do
  echo "--- dns_server=$s ---"
  ping -c 1 -W 1 "$s" >/dev/null 2>&1 && echo "ping=ok" || echo "ping=fail"
  timeout 2 bash -lc "cat < /dev/null > /dev/tcp/$s/53" >/dev/null 2>&1 && echo "tcp53=open" || echo "tcp53=closed_or_filtered"
done

section "DNS BOUNDARY"
echo "read_only=true"
echo "does_not_modify_dns=true"
echo "does_not_reload_resolved=true"
echo "does_not_touch_opnsense=true"
