#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="/home/ogre/spot-stack/watch"
STATE_DIR="${BASE_DIR}/state"
LOG_DIR="${BASE_DIR}/logs"
POLICY_FILE="${BASE_DIR}/fleet-policy.json"
REMEDIATION_STATE_FILE="${BASE_DIR}/state/remediation-state.json"
ROUTING_AUDIT_SUMMARY_FILE="${STATE_DIR}/routing-audit-summary.json"

mkdir -p "$STATE_DIR" "$LOG_DIR"
[[ -f "$REMEDIATION_STATE_FILE" ]] || echo "{}" > "$REMEDIATION_STATE_FILE"

STAMP="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
STATE_FILE="${STATE_DIR}/fleet-status.json"
LOG_FILE="${LOG_DIR}/fleet-watch.log"
TMP_FILE="$(mktemp)"

jq empty "$POLICY_FILE" >/dev/null 2>&1 || {
  echo "ALERT policy_invalid_json" | tee -a "$LOG_FILE"
  exit 1
}

declare -A HOST_IPS=(
  ["spot-core"]="127.0.0.1"
  ["spot-worker-01"]="192.168.10.10"
  ["spot-worker-02"]="192.168.10.11"
  ["spot-worker-03"]="192.168.10.13"
  ["spot-worker-04"]="192.168.10.14"
  ["spot-worker-05"]="192.168.10.15"
  ["spot-worker-06"]="192.168.10.16"
  ["spot-ui-01"]="192.168.10.12"
  ["starfleet-tower"]="192.168.30.5"
  ["starfleet-core"]="192.168.60.20"
  ["dns-core"]="192.168.60.10"
)

HOSTS=(
  "spot-core"
  "spot-worker-01"
  "spot-worker-02"
  "spot-worker-03"
  "spot-worker-04"
  "spot-worker-05"
  "spot-worker-06"
  "spot-ui-01"
  "starfleet-tower"
  "starfleet-core"
  "dns-core"
)

GOOD_DNS_1="192.168.60.10"
GOOD_DNS_2="192.168.60.20"

json_escape() { python3 - <<'PY' "$1"
import json, sys
print(json.dumps(sys.argv[1]))
PY
}

ssh_quick() {
  local host="$1"; shift
  local target="$host"
  if [[ -n "${HOST_IPS[$host]:-}" ]]; then target="ogre@${HOST_IPS[$host]}"; fi
  ssh -i "$HOME/.ssh/spot_fleet" \
  -o IdentitiesOnly=yes \
  -o BatchMode=yes \
  -o ConnectTimeout=5 \
  "$target" "$@"
}

check_http() { curl -fsS --max-time 5 "$1" >/dev/null 2>&1; }

fetch_routing_audit_summary() {
  local url="http://127.0.0.1:8787/stats/routing-audit?limit=200"
  if curl -fsS --max-time 5 "$url" > "$ROUTING_AUDIT_SUMMARY_FILE.tmp"; then
    if jq empty "$ROUTING_AUDIT_SUMMARY_FILE.tmp" >/dev/null 2>&1; then
      mv "$ROUTING_AUDIT_SUMMARY_FILE.tmp" "$ROUTING_AUDIT_SUMMARY_FILE"
      return 0
    fi
  fi
  rm -f "$ROUTING_AUDIT_SUMMARY_FILE.tmp"
  cat > "$ROUTING_AUDIT_SUMMARY_FILE" <<'JSON'
{"ok":false,"error":"routing_audit_unavailable","primaries":0,"fallbacks":0,"violations":0,"manual_overrides":0,"window_count":0,"last_violation_ts":null,"by_role":{},"items":[]}
JSON
  return 1
}

routing_audit_ok=true
if ! fetch_routing_audit_summary; then routing_audit_ok=false; fi
ROUTING_AUDIT_JSON="$(cat "$ROUTING_AUDIT_SUMMARY_FILE")"
CORE_HEALTH_RAW="$(curl -fsS --max-time 5 http://127.0.0.1:8787/health 2>/dev/null || true)"
if echo "$CORE_HEALTH_RAW" | jq -e '.ok' >/dev/null 2>&1; then CORE_HEALTH_JSON="$CORE_HEALTH_RAW"; else CORE_HEALTH_JSON='{"ok":false,"uptime_sec":0}'; fi
DNS_FIX_QUEUE=()

{
  echo "{"
  echo "  \"timestamp\": $(json_escape "$STAMP"),"
  echo "  \"core_health\": ${CORE_HEALTH_JSON},"
  echo "  \"routing_audit\": ${ROUTING_AUDIT_JSON},"
  echo "  \"hosts\": {"
  first=1
  for host in "${HOSTS[@]}"; do
    [[ $first -eq 0 ]] && echo ","
    first=0
    ssh_ok=false; service_ok=null; models_json="[]"; alerts_json="[]"; quarantined=false; eligible=false
    gpu_free_mb_max=null; gpu_vram_total_mb_max=null; load_1=null; running_jobs=0
    dns_ok=null; dns_servers_json="[]"; dns_mode="unknown"
    if [[ "$host" == "spot-core" ]]; then ssh_ok=true; elif ssh_quick "$host" "hostname" >/dev/null 2>&1; then ssh_ok=true; fi
    if [[ "$ssh_ok" == true ]]; then
      if [[ "$host" == "spot-core" ]]; then dns_raw="$(cat /etc/resolv.conf 2>/dev/null || true)"; else dns_raw="$(ssh_quick "$host" "cat /etc/resolv.conf 2>/dev/null" || true)"; fi
      dns_list="$(echo "$dns_raw" | awk '/nameserver/ {print $2}' | sort -u | tr '\n' ' ')"
      if [[ -n "$dns_list" ]]; then dns_servers_json="$(printf '%s\n' $dns_list | sed '/^$/d' | jq -R . | jq -s .)"; fi
      if echo "$dns_raw" | grep -q "127.0.0.53"; then
        dns_mode="stub"
        if [[ "$host" == "spot-core" ]]; then resolved_status="$(resolvectl status 2>/dev/null || true)"; else resolved_status="$(ssh_quick "$host" "resolvectl status 2>/dev/null || true" || true)"; fi
        if echo "$resolved_status" | grep -q "DNS Servers: $GOOD_DNS_1 $GOOD_DNS_2"; then dns_ok=true; dns_servers_json="$(printf '%s\n%s\n' "$GOOD_DNS_1" "$GOOD_DNS_2" | jq -R . | jq -s .)"; else dns_ok=false; fi
      elif echo "$dns_raw" | grep -Eq '^\s*nameserver\s+127\.0\.0\.1$'; then
        dns_mode="local"; [[ "$host" == "dns-core" ]] && dns_ok=true || dns_ok=false; dns_servers_json='["127.0.0.1"]'
      else
        dns_mode="static"; expected_dns="$(printf '%s\n%s\n' "$GOOD_DNS_1" "$GOOD_DNS_2" | sort | tr '\n' ' ')"; [[ "$dns_list" == "$expected_dns" ]] && dns_ok=true || dns_ok=false
      fi
    fi
    if [[ "$host" == spot-worker-* ]]; then
      if check_http "http://${HOST_IPS[$host]}:11434/api/tags"; then service_ok=true; models_json="$(curl -fsS --max-time 5 "http://${HOST_IPS[$host]}:11434/api/tags" | jq -c '[.models[].name]')"; else service_ok=false; fi
      if [[ "$ssh_ok" == true ]]; then
        load_1="$(ssh_quick "$host" "awk '{print \$1}' /proc/loadavg" 2>/dev/null | tr -d '\r' || true)"; [[ -z "$load_1" ]] && load_1=null
        gpu_csv="$(ssh_quick "$host" "nvidia-smi --query-gpu=memory.total,memory.free --format=csv,noheader,nounits" 2>/dev/null | tr -d '\r' || true)"
        if [[ -n "$gpu_csv" ]]; then
          gpu_vram_total_mb_max="$(printf '%s\n' "$gpu_csv" | awk -F',' 'BEGIN { max = -1 } { gsub(/ /, "", $1); if (($1 + 0) > max) max = ($1 + 0) } END { if (max >= 0) print max }')"
          gpu_free_mb_max="$(printf '%s\n' "$gpu_csv" | awk -F',' 'BEGIN { max = -1 } { gsub(/ /, "", $2); if (($2 + 0) > max) max = ($2 + 0) } END { if (max >= 0) print max }')"
        fi
        [[ -z "${gpu_vram_total_mb_max}" ]] && gpu_vram_total_mb_max=null; [[ -z "${gpu_free_mb_max}" ]] && gpu_free_mb_max=null
        running_jobs="$(ssh_quick "$host" "ps aux | grep -E 'ollama (run|serve)' | grep -v grep | wc -l" 2>/dev/null | tr -d '\r' || true)"; [[ -z "$running_jobs" ]] && running_jobs=0
      fi
    elif [[ "$host" == "spot-core" ]]; then
      if check_http "http://127.0.0.1:8787/health"; then service_ok=true; else service_ok=false; fi
    fi
    read -r alerts_json quarantined eligible <<< "$(python3 - <<'PY' "$host" "$POLICY_FILE" "$REMEDIATION_STATE_FILE" "$ssh_ok" "$service_ok" "$models_json" "$dns_ok"
import json, sys
host, policy_path, remediation_state_path = sys.argv[1], sys.argv[2], sys.argv[3]
ssh_ok = sys.argv[4] == "true"
service_ok_raw = sys.argv[5]
models = json.loads(sys.argv[6])
dns_ok_raw = sys.argv[7]
dns_ok = None if dns_ok_raw == "null" else (dns_ok_raw == "true")
service_ok = None if service_ok_raw == "null" else (service_ok_raw == "true")
alerts = []
if not ssh_ok: alerts.append("ssh_down")
if service_ok is False: alerts.append("service_down")
if dns_ok is False: alerts.append("dns_bad")
with open(policy_path, "r", encoding="utf-8") as f: policy = json.load(f)
for model in policy.get("required_models", {}).get(host, []):
    if service_ok is True and model not in models: alerts.append(f"missing_model:{model}")
try:
    with open(remediation_state_path, "r", encoding="utf-8") as f: rem_state = json.load(f)
except Exception: rem_state = {}
entry = rem_state.get(host, {})
quarantined = bool(entry.get("quarantined", False)) if isinstance(entry, dict) else False
eligible = host.startswith("spot-worker-") and ssh_ok and service_ok is True and not quarantined and len(alerts) == 0
print(json.dumps(alerts, separators=(",", ":")), str(quarantined).lower(), str(eligible).lower())
PY
)"
    if echo "$alerts_json" | jq -e '.[] | select(. == "dns_bad")' >/dev/null 2>&1; then DNS_FIX_QUEUE+=("$host"); fi
    echo -n "    $(json_escape "$host"): {"
    echo -n "\"ssh_ok\": ${ssh_ok}, "
    if [[ "$service_ok" == "null" ]]; then echo -n "\"service_ok\": null, "; else echo -n "\"service_ok\": ${service_ok}, "; fi
    echo -n "\"models\": ${models_json}, \"gpu_free_mb_max\": ${gpu_free_mb_max}, \"gpu_vram_total_mb_max\": ${gpu_vram_total_mb_max}, \"load_1\": ${load_1}, \"running_jobs\": ${running_jobs}, \"alerts\": ${alerts_json}, \"dns\": {\"ok\": ${dns_ok}, \"servers\": ${dns_servers_json}, \"mode\": \"${dns_mode}\"}, \"quarantined\": ${quarantined}, \"eligible\": ${eligible}"
    echo -n "}"
  done
  echo
  echo "  }"
  echo "}"
} > "$TMP_FILE"

if ! python3 -m json.tool "$TMP_FILE" >/dev/null 2>&1; then
  echo "ALERT fleet_status_invalid_json" | tee -a "$LOG_FILE"
  cat "$TMP_FILE" > "${STATE_FILE}.bad.$(date -u +%Y%m%dT%H%M%SZ)"
  rm -f "$TMP_FILE"
  exit 1
fi
mv -f "$TMP_FILE" "$STATE_FILE"
if (( ${#DNS_FIX_QUEUE[@]} > 0 )); then
  for host in "${DNS_FIX_QUEUE[@]}"; do echo "[ACTION] dns_bad on $host" | tee -a "$LOG_FILE"; ~/spot-stack/watch/fix-dns.sh "$host" >> "$LOG_FILE" 2>&1 || true; done
fi
python3 - <<'PY' "$STATE_FILE" "$routing_audit_ok" | tee -a "$LOG_FILE"
import json, sys, time
state_path = sys.argv[1]
routing_fetch_ok = sys.argv[2] == "true"
with open(state_path, "r", encoding="utf-8") as f: data = json.load(f)
alerts = []
for host, info in data["hosts"].items():
    for alert in info.get("alerts", []): alerts.append(f"{host}:{alert}")
    if info.get("quarantined"): alerts.append(f"{host}:quarantined")
audit = data.get("routing_audit", {})
violations = int(audit.get("violations", 0) or 0)
last_violation_ts = audit.get("last_violation_ts")
recent_violation = False
try:
    if last_violation_ts is not None:
        recent_violation = (int(time.time()) - int(last_violation_ts)) <= 3600
except Exception:
    recent_violation = True
if not routing_fetch_ok: alerts.append("spot-core:routing_audit_unavailable")
if violations > 0 and recent_violation:
    alerts.append(f"routing_audit:violations={violations}")
    if last_violation_ts is not None: alerts.append(f"routing_audit:last_violation_ts={last_violation_ts}")
print("ALERT " + " | ".join(alerts) if alerts else "OK fleet healthy | routing clean")
PY
