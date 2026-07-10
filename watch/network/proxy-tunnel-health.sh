#!/usr/bin/env bash
set -u

UNITS=(
  caddy.service
  cloudflared.service
  spot-bridge.service
  spot-mcp.service
  starfleet-ui.service
)

PORTS=(
  "8787:Spot Core API"
  "8010:Spot Bridge API"
  "7681:Spot terminal"
  "80:HTTP"
  "443:HTTPS"
)

pass=0
warn=0

echo "=== SPOT REVERSE PROXY / TUNNEL HEALTH ==="
echo "timestamp: $(date -Is)"
echo "host: $(hostname)"
echo

echo "services:"
for unit in "${UNITS[@]}"; do
  load_state="$(systemctl show "$unit" \
    --property=LoadState --value 2>/dev/null || true)"
  active_state="$(systemctl is-active "$unit" 2>/dev/null || true)"

  if [[ "$load_state" == "not-found" || -z "$load_state" ]]; then
    printf '  %-28s %s\n' "$unit" "NOT-INSTALLED"
    continue
  fi

  if [[ "$active_state" == "active" ]]; then
    printf '  %-28s %s\n' "$unit" "PASS"
    pass=$((pass + 1))
  else
    printf '  %-28s %s\n' "$unit" "WARN:${active_state:-unknown}"
    warn=$((warn + 1))
  fi
done

echo
echo "listening ports:"
listen_data="$(ss -lntH 2>/dev/null || true)"

for entry in "${PORTS[@]}"; do
  port="${entry%%:*}"
  label="${entry#*:}"

  if awk -v p=":${port}" '$4 ~ p"$" {found=1} END {exit !found}' \
    <<<"$listen_data"; then
    printf '  %-24s port=%-5s %s\n' "$label" "$port" "PASS"
    pass=$((pass + 1))
  else
    printf '  %-24s port=%-5s %s\n' "$label" "$port" "NOT-LISTENING"
  fi
done

echo
echo "local endpoint probes:"

probe() {
  local label="$1"
  local url="$2"
  local code

  code="$(curl -k -sS -o /dev/null \
    --connect-timeout 2 \
    --max-time 5 \
    -w '%{http_code}' \
    "$url" 2>/dev/null || true)"

  if [[ "$code" =~ ^[123][0-9][0-9]$ ]]; then
    printf '  %-24s %-34s HTTP %s PASS\n' "$label" "$url" "$code"
    pass=$((pass + 1))
  elif [[ "$code" =~ ^[45][0-9][0-9]$ ]]; then
    printf '  %-24s %-34s HTTP %s REACHABLE\n' "$label" "$url" "$code"
    pass=$((pass + 1))
  else
    printf '  %-24s %-34s %s\n' "$label" "$url" "NO-RESPONSE"
  fi
}

probe "Spot Core"   "http://127.0.0.1:8787/"
probe "Spot Bridge" "http://127.0.0.1:8010/"
probe "Local HTTP"  "http://127.0.0.1/"

echo
echo "summary: pass=${pass} warn=${warn}"

if (( warn == 0 )); then
  echo "overall: HEALTHY_OR_NOT_CONFIGURED"
else
  echo "overall: DEGRADED"
fi

echo "mode: read-only"
echo "mutation_performed: false"
