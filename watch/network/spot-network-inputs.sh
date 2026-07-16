#!/usr/bin/env bash
set -Eeuo pipefail

section() { printf '\n===== %s =====\n' "$*"; }

section "SPOT NETWORK INPUTS"
echo "timestamp=$(date -Is)"
echo "host=$(hostname)"
echo "mode=read_only"
echo "mutation_authority=false"
echo "high_risk_network_change=false"

section "LOCAL IDENTITY"
hostnamectl 2>/dev/null || true
ip -br addr 2>/dev/null || true

section "ROUTES"
ip route 2>/dev/null || true

section "DNS CONFIG"
resolvectl status 2>/dev/null || cat /etc/resolv.conf 2>/dev/null || true

section "HOST RESOLUTION"
for h in \
  spot-core \
  starfleet-tower \
  spot-ui-01 \
  spot-worker-01 \
  spot-worker-02 \
  spot-worker-03 \
  spot-worker-04 \
  spot-worker-05 \
  spot-worker-06 \
  unimatrix6 \
  starfleet-core \
  dns-core \
  starfleet-edge-01
do
  printf '%-22s ' "$h"
  getent hosts "$h" || echo "unresolved"
done

section "LOCAL HOST FILE REFERENCES"
grep -nE 'spot-|starfleet|unimatrix|dns-core|edge' /etc/hosts 2>/dev/null || true

section "NETPLAN / NETWORK CONFIG FILES"
find /etc/netplan /etc/systemd/network -maxdepth 2 -type f 2>/dev/null | sort | while read -r f; do
  echo "--- $f ---"
  sed -n '1,160p' "$f" 2>/dev/null || true
done

section "MOUNTS"
findmnt /mnt/collective /mnt/unimatrix6 /mnt/ai-data 2>/dev/null || true
df -h | egrep '/mnt/collective|/mnt/unimatrix6|/mnt/ai-data|unimatrix6|192.168.50.10' || true

section "LISTENERS"
ss -lntup 2>/dev/null | egrep ':22|:53|:80|:443|:5173|:7681|:8010|:8787|:11434' || true

section "KNOWN INPUT SOURCES"
cat <<MAP
fleet_status=/home/ogre/spot-stack/watch/state/fleet-status.json
routing_audit=/home/ogre/spot-stack/watch/state/routing-audit.jsonl
routing_audit_summary=/home/ogre/spot-stack/watch/state/routing-audit-summary.json
unimatrix_storage=/mnt/collective
spot_edge_status=/mnt/collective/logs/spot/edge/starfleet-edge-01
spot_api=http://127.0.0.1:8787
bridge_api=http://127.0.0.1:8010
ui=http://127.0.0.1:5173
terminal=http://127.0.0.1:7681
MAP

section "BOUNDARY"
echo "read_only=true"
echo "does_not_modify_dns=true"
echo "does_not_modify_routes=true"
echo "does_not_modify_firewall=true"
