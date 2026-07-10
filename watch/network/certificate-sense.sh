#!/usr/bin/env bash
set -u

SERVICE_UNITS=(
  caddy.service
  cloudflared.service
  spot-bridge-api.service
  spot-mcp.service
  spot-ui-publish.service
  starfleet-ui.service
)

CADDY_FILES=(
  /etc/caddy/Caddyfile
  /etc/caddy/conf.d
)

pass=0
warn=0

echo "===== SPOT CERTIFICATE AND ENDPOINT SENSE ====="
echo "timestamp=$(date -Is)"
echo "host=$(hostname)"
echo "mode=read_only"
echo "mutation_authority=false"
echo

echo "===== SERVICE STATE ====="

for unit in "${SERVICE_UNITS[@]}"; do
  load_state="$(
    systemctl show "$unit" \
      --property=LoadState \
      --value 2>/dev/null || true
  )"

  active_state="$(systemctl is-active "$unit" 2>/dev/null || true)"

  if [[ "$load_state" == "not-found" || -z "$load_state" ]]; then
    printf '%-30s %s\n' "$unit" "NOT-INSTALLED"
  elif [[ "$active_state" == "active" ]]; then
    printf '%-30s %s\n' "$unit" "PASS"
    pass=$((pass + 1))
  else
    printf '%-30s %s\n' "$unit" "WARN:${active_state:-unknown}"
    warn=$((warn + 1))
  fi
done

echo
echo "===== LOCAL ENDPOINTS ====="

probe_http() {
  local label="$1"
  local url="$2"
  local code

  code="$(
    curl -k -sS \
      -o /dev/null \
      --connect-timeout 2 \
      --max-time 8 \
      -w '%{http_code}' \
      "$url" 2>/dev/null || true
  )"

  if [[ "$code" =~ ^[1-5][0-9][0-9]$ ]]; then
    printf '%-24s %-36s HTTP %s REACHABLE\n' "$label" "$url" "$code"
    pass=$((pass + 1))
  else
    printf '%-24s %-36s NO-RESPONSE\n' "$label" "$url"
    warn=$((warn + 1))
  fi
}

probe_http "Spot Core API"   "http://127.0.0.1:8787/"
probe_http "Spot Bridge API" "http://127.0.0.1:8010/"
probe_http "Local Caddy"     "http://127.0.0.1/"

echo
echo "===== DISCOVERED CADDY HOSTS ====="

mapfile -t HOSTS < <(
  for path in "${CADDY_FILES[@]}"; do
    if [[ -f "$path" ]]; then
      cat "$path"
    elif [[ -d "$path" ]]; then
      find "$path" \
        -maxdepth 2 \
        -type f \
        -readable \
        -exec cat {} + 2>/dev/null
    fi
  done |
    sed 's/#.*$//' |
    grep -Eo \
      '([A-Za-z0-9_-]+\.)+[A-Za-z]{2,}(:[0-9]+)?' |
    sed 's/:[0-9][0-9]*$//' |
    sort -u
)

if (( ${#HOSTS[@]} == 0 )); then
  echo "discovered_hosts=none"
else
  printf 'discovered_host=%s\n' "${HOSTS[@]}"
fi

echo
echo "===== TLS CERTIFICATES ====="

for host in "${HOSTS[@]}"; do
  cert="$(
    timeout 10 openssl s_client \
      -connect "${host}:443" \
      -servername "$host" \
      -showcerts </dev/null 2>/dev/null |
      openssl x509 -noout \
        -subject \
        -issuer \
        -serial \
        -dates 2>/dev/null || true
  )"

  if [[ -n "$cert" ]]; then
    echo "--- ${host}:443 ---"
    printf '%s\n' "$cert"

    if timeout 10 openssl s_client \
      -connect "${host}:443" \
      -servername "$host" </dev/null 2>/dev/null |
      openssl x509 -checkend 1209600 -noout >/dev/null 2>&1; then
      echo "certificate_expiry_status=PASS_GT_14_DAYS"
      pass=$((pass + 1))
    else
      echo "certificate_expiry_status=WARN_WITHIN_14_DAYS_OR_UNVERIFIED"
      warn=$((warn + 1))
    fi
  else
    echo "--- ${host}:443 ---"
    echo "certificate_status=UNAVAILABLE"
    warn=$((warn + 1))
  fi

  code="$(
    curl -k -sS \
      -o /dev/null \
      --connect-timeout 3 \
      --max-time 10 \
      -w '%{http_code}' \
      "https://${host}/" 2>/dev/null || true
  )"

  if [[ "$code" =~ ^[1-5][0-9][0-9]$ ]]; then
    echo "https_status=${code}"
    pass=$((pass + 1))
  else
    echo "https_status=NO-RESPONSE"
    warn=$((warn + 1))
  fi

  echo
done

echo "summary_pass=${pass}"
echo "summary_warn=${warn}"

if (( warn == 0 )); then
  echo "overall=HEALTHY"
else
  echo "overall=DEGRADED"
fi

echo "configuration_modified=false"
echo "mutation_performed=false"
