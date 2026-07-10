#!/usr/bin/env bash
set -Eeuo pipefail

section() { printf '\n===== %s =====\n' "$*"; }

section "SPOT GATEWAY SENSE"
echo "timestamp=$(date -Is)"
echo "host=$(hostname)"
echo "mode=read_only"
echo "mutation_authority=false"

section "ROUTE TABLE"
ip route 2>/dev/null || true

section "DEFAULT GATEWAYS"
gateways="$(ip route 2>/dev/null | awk '/^default/ {print $3}' | sort -u || true)"
if [ -z "$gateways" ]; then
  echo "default_gateway=not_found"
else
  for gw in $gateways; do
    echo "--- gateway=$gw ---"
    ping -c 3 -W 1 "$gw" || true
    ip neigh show "$gw" 2>/dev/null || true
  done
fi

section "CRITICAL VLAN / SUBNET TARGETS"
for target in \
  192.168.10.1 \
  192.168.30.5 \
  192.168.50.10 \
  192.168.60.1 \
  192.168.60.10 \
  192.168.60.20
do
  echo "--- target=$target ---"
  ping -c 1 -W 1 "$target" >/dev/null 2>&1 && echo "ping=ok" || echo "ping=fail"
  ip route get "$target" 2>/dev/null || true
done

section "PUBLIC EGRESS PROBE"
for target in 1.1.1.1 8.8.8.8; do
  echo "--- target=$target ---"
  ping -c 1 -W 1 "$target" >/dev/null 2>&1 && echo "ping=ok" || echo "ping=fail"
  ip route get "$target" 2>/dev/null || true
done

section "BOUNDARY"
echo "read_only=true"
echo "does_not_modify_routes=true"
echo "does_not_modify_gateway=true"
echo "does_not_touch_firewall=true"
