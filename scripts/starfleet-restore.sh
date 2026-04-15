#!/usr/bin/env bash
set -euo pipefail

echo "==============================="
echo " STARFLEET RESTORE INITIATED"
echo "==============================="

BASE="$HOME/spot-AI"

GW_SRC="$BASE/nodes/spot/spot-gateway-app.py"
GW_DST="/opt/spot-gateway/app.py"

PROBE_SRC="$BASE/scripts/fleet-dispatch-probes"
PROBE_DST="/usr/local/bin/fleet-dispatch-probes"

echo "[1/6] Restoring gateway..."
if [[ -f "$GW_SRC" ]]; then
  sudo cp -av "$GW_SRC" "$GW_DST"
else
  echo "ERROR: gateway source not found: $GW_SRC"
  exit 1
fi

echo "[2/6] Restoring fleet probes..."
if [[ -f "$PROBE_SRC" ]]; then
  sudo cp -av "$PROBE_SRC" "$PROBE_DST"
  sudo chmod +x "$PROBE_DST"
else
  echo "ERROR: probe script not found: $PROBE_SRC"
  exit 1
fi

echo "[3/6] Restarting gateway..."
sudo systemctl restart spot-gateway
sleep 2

echo "[4/6] Verifying gateway health..."
if curl -sS http://127.0.0.1:8798/health | jq -e '.ok == true' >/dev/null; then
  echo "Gateway OK"
else
  echo "ERROR: gateway health failed"
  systemctl status spot-gateway --no-pager
  exit 1
fi

echo "[5/6] Checking GPU cluster status..."
curl -sS http://127.0.0.1:8798/cluster/gpu_status | jq -r '
  .workers | to_entries[] |
  "\(.key): \(.value.selected_gpu.name) | free=\(.value.selected_gpu.vram_free_mb)MB | temp=\(.value.selected_gpu.temp_c)C"
'

echo "[6/6] Checking M-5 ollama status..."
M5_IP="192.168.10.11"
ssh ogre@$M5_IP 'systemctl is-enabled ollama || true'

echo
echo "==============================="
echo " FINAL FLEET STATUS"
echo "==============================="
fleet

echo
echo "==============================="
echo " RESTORE COMPLETE"
echo "==============================="

