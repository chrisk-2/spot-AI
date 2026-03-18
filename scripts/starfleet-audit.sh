#!/usr/bin/env bash
set -u

POLICY="$HOME/spot-AI/configs/node-policy.env"
[[ -f "$POLICY" ]] && source "$POLICY"

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
check "spot-gateway active" "active" "$(systemctl is-active "$SPOT_GATEWAY_UNIT" 2>/dev/null || echo unknown)"
check "$SPOT_WORKER_UNIT active" "active" "$(systemctl is-active "$SPOT_WORKER_UNIT" 2>/dev/null || echo unknown)"

echo
echo "[M-5 Checks]"
check "M-5 ollama disabled" "$M5_OLLAMA_SHOULD_BE" "$(remote_first_line "$M5_HOST" 'systemctl is-enabled ollama || true')"

for svc in $M5_WORKER_UNITS; do
  state="$(remote_first_line "$M5_HOST" "systemctl is-active $svc || true")"
  check "M-5 $svc active" "active" "$state"
done

echo
echo "[Daystrom Checks]"
for svc in $DAYSTROM_WORKER_UNITS; do
  state="$(remote_first_line "$DAYSTROM_HOST" "systemctl is-active $svc || true")"
  check "Daystrom $svc active" "active" "$state"
done

echo
echo "[Gateway Health]"
gw_ok="$(curl -sS "$GATEWAY_HEALTH_URL" | jq -r '.ok' 2>/dev/null || echo false)"
check "gateway health" "true" "$gw_ok"

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
