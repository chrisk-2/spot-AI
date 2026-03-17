#!/usr/bin/env bash
set -u

echo "==============================="
echo " STARFLEET CONFIG AUDIT"
echo "==============================="

fail=0

check() {
  local name="$1"
  local expected="$2"
  local actual="$3"

  if [[ "$actual" == "$expected" ]]; then
    echo "[OK]   $name -> $actual"
  else
    echo "[FAIL] $name -> expected=$expected actual=$actual"
    fail=1
  fi
}

remote_first_line() {
  local host="$1"
  local cmd="$2"
  ssh -o BatchMode=yes -o ConnectTimeout=5 "ogre@$host" "$cmd" 2>/dev/null | head -n1 | tr -d '\r'
}

echo
echo "[Spot Node Checks]"
check "spot-gateway active" "active" "$(systemctl is-active spot-gateway 2>/dev/null || echo unknown)"
check "spot-worker0 active" "active" "$(systemctl is-active spot-worker0 2>/dev/null || echo unknown)"

echo
echo "[M-5 Checks]"
M5="192.168.10.11"
check "M-5 ollama disabled" "disabled" "$(remote_first_line "$M5" 'systemctl is-enabled ollama || true')"
check "M-5 worker6 active" "active" "$(remote_first_line "$M5" 'systemctl is-active spot-worker6 || true')"
check "M-5 worker8 active" "active" "$(remote_first_line "$M5" 'systemctl is-active spot-worker8 || true')"

echo
echo "[Daystrom Checks]"
DAY="192.168.10.13"
check "Daystrom worker2 active" "active" "$(remote_first_line "$DAY" 'systemctl is-active spot-worker2 || true')"

echo
echo "[Gateway Health]"
check "gateway health" "true" "$(curl -sS http://127.0.0.1:8798/health | jq -r '.ok' 2>/dev/null || echo false)"

echo
echo "[Dispatch Sanity]"
if fleet | grep -q "FAIL"; then
  echo "[FAIL] fleet dispatch has failures"
  fail=1
else
  echo "[OK]   fleet dispatch clean"
fi

echo
echo "==============================="
if [[ "$fail" -eq 0 ]]; then
  echo " AUDIT PASS"
else
  echo " AUDIT FAIL"
fi
echo "==============================="

exit "$fail"
