#!/usr/bin/env bash
set -u

NODES=(
  "spot-worker-01:192.168.10.10"
  "spot-worker-02:192.168.10.11"
  "spot-worker-03:192.168.10.13"
  "spot-worker-04:192.168.10.14"
  "starfleet-tower:192.168.30.5"
  "unimatrix6:192.168.50.10"
  "starfleet-core:192.168.60.20"
  "dns-core:192.168.60.10"
)

GOOD_DNS_1="192.168.60.10"
GOOD_DNS_2="192.168.60.20"

PASS_COUNT=0
WARN_COUNT=0
FAIL_COUNT=0

pass() {
  PASS_COUNT=$((PASS_COUNT + 1))
  echo "[PASS] $*"
}

warn() {
  WARN_COUNT=$((WARN_COUNT + 1))
  echo "[WARN] $*"
}

fail() {
  FAIL_COUNT=$((FAIL_COUNT + 1))
  echo "[FAIL] $*"
}

echo "=== SPOT FLEET DNS AUDIT v2 ==="
echo "timestamp: $(date -u +"%Y-%m-%dT%H:%M:%SZ")"
echo "expected upstream dns: $GOOD_DNS_1, $GOOD_DNS_2"
echo

for entry in "${NODES[@]}"; do
  name="${entry%%:*}"
  host="${entry##*:}"

  echo "---- $name ($host) ----"

  if ! ssh -o BatchMode=yes -o ConnectTimeout=5 ogre@"$host" "echo ok" >/dev/null 2>&1; then
    fail "SSH unreachable or auth failed"
    echo
    continue
  fi

  current_dns="$(ssh -o BatchMode=yes ogre@"$host" "cat /etc/resolv.conf 2>/dev/null || echo missing")"

  echo "[INFO] current /etc/resolv.conf:"
  echo "$current_dns" | sed 's/^/  /'

  # dns-core is allowed to use itself locally
  if [[ "$name" == "dns-core" ]]; then
    if echo "$current_dns" | grep -Eq '^\s*nameserver\s+127\.0\.0\.1$'; then
      pass "dns-core using local resolver (127.0.0.1)"
      echo
      continue
    fi

    if echo "$current_dns" | grep -q 'nameserver 127.0.0.53'; then
      resolved_status="$(ssh -o BatchMode=yes ogre@"$host" "resolvectl status 2>/dev/null || true")"

      echo "[INFO] resolvectl status (filtered):"
      if [[ -n "$resolved_status" ]]; then
        echo "$resolved_status" | grep -E 'Current DNS Server:|DNS Servers:|DNS Domain:|resolv.conf mode:' | sed 's/^/  /'
      else
        echo "  unavailable"
      fi

    if echo "$resolved_status" | grep -q "resolv.conf mode: stub" && \
       echo "$resolved_status" | grep -q "DNS Servers: $GOOD_DNS_1 $GOOD_DNS_2"; then
      pass "systemd-resolved stub in use with correct upstream DNS"
    else
      warn "systemd-resolved stub present but upstream DNS does not match expected values"
    fi

      echo
      continue
    fi

    # Normalize DNS entries (works across Linux + DSM)
    dns_list=$(echo "$current_dns" | awk '/nameserver/ {print $2}' | sort -u | tr '\n' ' ')
    expected_dns=$(printf "%s\n%s\n" "$GOOD_DNS_1" "$GOOD_DNS_2" | sort | tr '\n' ' ')

    if [[ "$dns_list" == "$expected_dns" ]]; then
      pass "static Starfleet DNS correct"
      echo
      continue
    fi

    fail "dns-core resolver configuration does not match approved patterns"
    echo
    continue
  fi

  # Standard nodes: prefer resolved stub with correct upstreams
  if echo "$current_dns" | grep -q 'nameserver 127.0.0.53'; then
    resolved_status="$(ssh -o BatchMode=yes ogre@"$host" "resolvectl status 2>/dev/null || true")"

    echo "[INFO] resolvectl status (filtered):"
    if [[ -n "$resolved_status" ]]; then
      echo "$resolved_status" | grep -E 'Current DNS Server:|DNS Servers:|DNS Domain:|resolv.conf mode:' | sed 's/^/  /'
    else
      echo "  unavailable"
    fi

    if [[ -z "$resolved_status" ]]; then
      fail "stub resolver present but resolvectl unavailable"
      echo
      continue
    fi

    if echo "$resolved_status" | grep -q "Current DNS Server: $GOOD_DNS_1" && \
       echo "$resolved_status" | grep -q "DNS Servers: $GOOD_DNS_1 $GOOD_DNS_2"; then
      pass "systemd-resolved stub in use with correct upstream DNS"
    else
      warn "systemd-resolved stub present but upstream DNS does not match expected values"
    fi

    echo
    continue
  fi

    # Normalize DNS entries (works across Linux + DSM)
    dns_list=$(echo "$current_dns" | awk '/nameserver/ {print $2}' | sort -u | tr '\n' ' ')
    expected_dns=$(printf "%s\n%s\n" "$GOOD_DNS_1" "$GOOD_DNS_2" | sort | tr '\n' ' ')

    if [[ "$dns_list" == "$expected_dns" ]]; then
      pass "static Starfleet DNS correct"
      echo
      continue
    fi

  if echo "$current_dns" | grep -Eq '^\s*nameserver\s+1\.1\.1\.1$|^\s*nameserver\s+8\.8\.8\.8$|^\s*nameserver\s+8\.8\.4\.4$'; then
    warn "public resolver detected in /etc/resolv.conf"
    echo
    continue
  fi

  fail "unrecognized DNS configuration"
  echo
done

echo "=== SUMMARY ==="
echo "PASS: $PASS_COUNT"
echo "WARN: $WARN_COUNT"
echo "FAIL: $FAIL_COUNT"

if (( FAIL_COUNT > 0 )); then
  exit 2
fi

if (( WARN_COUNT > 0 )); then
  exit 1
fi

exit 0
