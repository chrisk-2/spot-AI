#!/usr/bin/env bash

set -euo pipefail

WORKERS=(
  "spot-worker-01:192.168.10.10"
  "spot-worker-02:192.168.10.11"
  "spot-worker-03:192.168.10.13"
  "spot-worker-04:192.168.10.14"
)

GOOD_DNS_1="192.168.60.10"
GOOD_DNS_2="192.168.60.20"

echo "=== SPOT FLEET DNS AUDIT + FIX ==="
echo "timestamp: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
echo

for entry in "${WORKERS[@]}"; do
  name="${entry%%:*}"
  host="${entry##*:}"

  echo "---- $name ($host) ----"

  if ! ssh -o BatchMode=yes -o ConnectTimeout=5 ogre@"$host" "echo ok" >/dev/null 2>&1; then
    echo "[FAIL] SSH unreachable"
    echo
    continue
  fi

  current_dns=$(ssh ogre@"$host" "cat /etc/resolv.conf 2>/dev/null || echo 'missing'")

  echo "[INFO] current resolv.conf:"
  echo "$current_dns" | sed 's/^/  /'

  if echo "$current_dns" | grep -q "$GOOD_DNS_1" && echo "$current_dns" | grep -q "$GOOD_DNS_2"; then
    echo "[PASS] DNS already correct"
  else
    echo "[FIX] applying correct DNS"

    ssh ogre@"$host" "sudo rm -f /etc/resolv.conf && sudo bash -c 'cat > /etc/resolv.conf <<EOT
nameserver $GOOD_DNS_1
nameserver $GOOD_DNS_2
EOT'"

    echo "[VERIFY] new resolv.conf:"
    ssh ogre@"$host" "cat /etc/resolv.conf" | sed 's/^/  /'
  fi

  echo "[TEST] dig check:"
  ssh ogre@"$host" "dig google.com +short | head -n 2" | sed 's/^/  /'

  echo
done

echo "=== DONE ==="
