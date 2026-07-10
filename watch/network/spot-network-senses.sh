#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"

section() { printf '\n===== %s =====\n' "$*"; }

section "SPOT NETWORK SENSES AGGREGATE"
echo "timestamp=$(date -Is)"
echo "host=$(hostname)"
echo "mode=read_only"
echo "mutation_authority=false"
echo "root=$ROOT"

for script in \
  "$ROOT/watch/network/spot-network-inputs.sh" \
  "$ROOT/watch/network/spot-dns-sense.sh" \
  "$ROOT/watch/network/spot-gateway-sense.sh" \
  "$ROOT/watch/network/spot-service-sense.sh"
do
  section "RUN $(basename "$script")"
  if [ -x "$script" ]; then
    "$script" || true
  else
    echo "missing_or_not_executable=$script"
  fi
done

section "AGGREGATE BOUNDARY"
echo "read_only=true"
echo "does_not_modify_network=true"
echo "does_not_modify_dns=true"
echo "does_not_modify_firewall=true"
echo "does_not_restart_services=true"
