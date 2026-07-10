#!/usr/bin/env bash
set -Eeuo pipefail

section() { printf '\n===== %s =====\n' "$*"; }

curl_head() {
  local name="$1" url="$2"
  echo "--- $name $url ---"
  curl -fsSI --connect-timeout 3 --max-time 5 "$url" 2>/dev/null | head -8 || echo "http=fail"
}

curl_json() {
  local name="$1" url="$2"
  echo "--- $name $url ---"
  curl -fsS --connect-timeout 3 --max-time 5 "$url" 2>/dev/null | jq -c . 2>/dev/null || echo "json=fail"
}

section "SPOT SERVICE SENSE"
echo "timestamp=$(date -Is)"
echo "host=$(hostname)"
echo "mode=read_only"
echo "mutation_authority=false"

section "LOCAL SERVICES"
systemctl list-units --type=service --state=running '*spot*' '*starfleet*' '*caddy*' '*cloudflared*' '*ssh*' --no-pager || true

section "FAILED SERVICES"
systemctl --failed --no-pager || true

section "LISTENERS"
ss -lntup 2>/dev/null | egrep ':22|:53|:80|:443|:5173|:7681|:8010|:8787|:11434' || true

section "HTTP CHECKS"
curl_json "spot-core-health" "http://127.0.0.1:8787/health"
curl_json "spot-runtime" "http://127.0.0.1:8787/stats/runtime"
curl_json "spot-routing-audit" "http://127.0.0.1:8787/stats/routing-audit"
curl_head "starfleet-ui-direct" "http://127.0.0.1:5173/"
curl_head "caddy-host-header" "http://127.0.0.1/"

section "WORKER OLLAMA PORTS"
for h in spot-worker-01 spot-worker-02 spot-worker-03 spot-worker-04 spot-worker-05 spot-worker-06; do
  echo "--- $h ---"
  getent hosts "$h" || true
  timeout 2 bash -lc "cat < /dev/null > /dev/tcp/$h/22" >/dev/null 2>&1 && echo "ssh22=open" || echo "ssh22=closed"
  timeout 2 bash -lc "cat < /dev/null > /dev/tcp/$h/11434" >/dev/null 2>&1 && echo "ollama11434=open" || echo "ollama11434=closed"
done

section "BOUNDARY"
echo "read_only=true"
echo "does_not_restart_services=true"
echo "does_not_modify_caddy=true"
echo "does_not_modify_cloudflare=true"
