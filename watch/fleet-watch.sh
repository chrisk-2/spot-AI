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
  ["spot-ui-01"]="192.168.10.12"
)

HOSTS=(
  "spot-core"
  "spot-worker-01"
  "spot-worker-02"
  "spot-worker-03"
  "spot-worker-04"
  "spot-ui-01"
)

json_escape() {
  python3 - <<'PY' "$1"
import json, sys
print(json.dumps(sys.argv[1]))
PY
}

ssh_quick() {
  local host="$1"
  shift
  ssh -o BatchMode=yes -o ConnectTimeout=5 "$host" "$@"
}

check_http() {
  local url="$1"
  curl -fsS --max-time 5 "$url" >/dev/null 2>&1
}

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
{"ok":false,"error":"routing_audit_unavailable","primaries":0,"fallbacks":0,"violations":0,"manual_overrides":0,"window_count":0,"last_violation_ts":null,"by_role":{}, "items":[]}
JSON
  return 1
}

routing_audit_ok=true
if ! fetch_routing_audit_summary; then
  routing_audit_ok=false
fi
ROUTING_AUDIT_JSON="$(cat "$ROUTING_AUDIT_SUMMARY_FILE")"

CORE_HEALTH_RAW="$(curl -fsS --max-time 5 http://127.0.0.1:8787/health 2>/dev/null || true)"

if echo "$CORE_HEALTH_RAW" | jq -e '.ok' >/dev/null 2>&1; then
  CORE_HEALTH_JSON="$CORE_HEALTH_RAW"
else
  CORE_HEALTH_JSON='{"ok":false,"uptime_sec":0}'
fi

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

    ssh_ok=false
    service_ok=null
    models_json="[]"
    alerts_json="[]"
    quarantined=false
    eligible=false
    gpu_free_mb_max=null
    gpu_vram_total_mb_max=null
    load_1=null
    running_jobs=0

    if [[ "$host" == "spot-core" ]]; then
      ssh_ok=true
    else
      if ssh_quick "$host" "hostname" >/dev/null 2>&1; then
        ssh_ok=true
      fi
    fi

    if [[ "$host" == spot-worker-* ]]; then
      if check_http "http://${HOST_IPS[$host]}:11434/api/tags"; then
        service_ok=true
        models_json="$(curl -fsS --max-time 5 "http://${HOST_IPS[$host]}:11434/api/tags" | jq -c '[.models[].name]')"
      else
        service_ok=false
      fi

      if [[ "$ssh_ok" == true ]]; then
        load_1="$(ssh_quick "$host" "awk '{print \$1}' /proc/loadavg" 2>/dev/null | tr -d '\r' || true)"
        [[ -z "$load_1" ]] && load_1=null

        gpu_csv="$(ssh_quick "$host" "nvidia-smi --query-gpu=memory.total,memory.free --format=csv,noheader,nounits" 2>/dev/null | tr -d '\r' || true)"

        if [[ -n "$gpu_csv" ]]; then
          gpu_vram_total_mb_max="$(printf '%s\n' "$gpu_csv" | awk -F',' '
            BEGIN { max = -1 }
            {
              gsub(/ /, "", $1)
              if (($1 + 0) > max) max = ($1 + 0)
            }
            END {
              if (max >= 0) print max
            }'
          )"

          gpu_free_mb_max="$(printf '%s\n' "$gpu_csv" | awk -F',' '
            BEGIN { max = -1 }
            {
              gsub(/ /, "", $2)
              if (($2 + 0) > max) max = ($2 + 0)
            }
            END {
              if (max >= 0) print max
            }'
          )"
        fi

        [[ -z "${gpu_vram_total_mb_max}" ]] && gpu_vram_total_mb_max=null
        [[ -z "${gpu_free_mb_max}" ]] && gpu_free_mb_max=null

        running_jobs="$(ssh_quick "$host" "ps aux | grep -E 'ollama (run|serve)' | grep -v grep | wc -l" 2>/dev/null | tr -d '\r' || true)"
        [[ -z "$running_jobs" ]] && running_jobs=0
      fi

    elif [[ "$host" == "spot-core" ]]; then
      if check_http "http://127.0.0.1:8787/health"; then
        service_ok=true
      else
        service_ok=false
      fi
    fi

    read -r alerts_json quarantined eligible <<< "$(python3 - <<'PY' \
      "$host" "$POLICY_FILE" "$REMEDIATION_STATE_FILE" "$ssh_ok" "$service_ok" "$models_json"
import json, sys

host = sys.argv[1]
policy_path = sys.argv[2]
remediation_state_path = sys.argv[3]
ssh_ok = sys.argv[4] == "true"
service_ok_raw = sys.argv[5]
models = json.loads(sys.argv[6])

service_ok = None if service_ok_raw == "null" else (service_ok_raw == "true")

alerts = []

if not ssh_ok:
    alerts.append("ssh_down")

if service_ok is False:
    alerts.append("service_down")

with open(policy_path, "r", encoding="utf-8") as f:
    policy = json.load(f)

required = policy.get("required_models", {}).get(host, [])
if service_ok is True:
    for model in required:
        if model not in models:
            alerts.append(f"missing_model:{model}")

try:
    with open(remediation_state_path, "r", encoding="utf-8") as f:
        rem_state = json.load(f)
except Exception:
    rem_state = {}

entry = rem_state.get(host, {})
if isinstance(entry, dict):
    quarantined = bool(entry.get("quarantined", False))
else:
    quarantined = False

eligible = (
    host.startswith("spot-worker-")
    and ssh_ok
    and service_ok is True
    and not quarantined
    and len(alerts) == 0
)

print(json.dumps(alerts), str(quarantined).lower(), str(eligible).lower())
PY
)"

    echo -n "    $(json_escape "$host"): {"
    echo -n "\"ssh_ok\": ${ssh_ok}, "
    if [[ "$service_ok" == "null" ]]; then
      echo -n "\"service_ok\": null, "
    else
      echo -n "\"service_ok\": ${service_ok}, "
    fi
    echo -n "\"models\": ${models_json}, "
    echo -n "\"gpu_free_mb_max\": ${gpu_free_mb_max}, "
    echo -n "\"gpu_vram_total_mb_max\": ${gpu_vram_total_mb_max}, "
    echo -n "\"load_1\": ${load_1}, "
    echo -n "\"running_jobs\": ${running_jobs}, "
    echo -n "\"alerts\": ${alerts_json}, "
    echo -n "\"quarantined\": ${quarantined}, "
    echo -n "\"eligible\": ${eligible}"
    echo -n "}"
  done

  echo
  echo "  }"
  echo "}"
} > "$TMP_FILE"

mv "$TMP_FILE" "$STATE_FILE"

python3 - <<'PY' "$STATE_FILE" "$routing_audit_ok" | tee -a "$LOG_FILE"
import json, sys

state_path = sys.argv[1]
routing_fetch_ok = sys.argv[2] == "true"

with open(state_path, "r", encoding="utf-8") as f:
    data = json.load(f)

alerts = []
for host, info in data["hosts"].items():
    for alert in info.get("alerts", []):
        alerts.append(f"{host}:{alert}")
    if info.get("quarantined"):
        alerts.append(f"{host}:quarantined")

audit = data.get("routing_audit", {})
violations = int(audit.get("violations", 0) or 0)
fallbacks = int(audit.get("fallbacks", 0) or 0)
last_violation_ts = audit.get("last_violation_ts")

if not routing_fetch_ok:
    alerts.append("spot-core:routing_audit_unavailable")

if violations > 0:
    alerts.append(f"routing_audit:violations={violations}")

if fallbacks > 0:
    alerts.append(f"routing_audit:fallbacks={fallbacks}")

if last_violation_ts is not None:
    alerts.append(f"routing_audit:last_violation_ts={last_violation_ts}")

if alerts:
    print("ALERT " + " | ".join(alerts))
else:
    print("OK fleet healthy | routing clean")
PY
