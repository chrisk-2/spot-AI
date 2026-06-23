#!/usr/bin/env bash
# spot-worker-recover.sh — autonomous worker SSH/service recovery
# Called by spot-self-heal.sh when a worker has ssh_down or service_down alerts.
# Usage: bash spot-worker-recover.sh <worker_name>
# Exit 0 = recovered, Exit 1 = not recovered (still down), Exit 2 = usage error
set -euo pipefail

WORKER="${1:-}"
if [[ -z "$WORKER" ]]; then
  echo "Usage: $(basename "$0") <worker_name>" >&2
  exit 2
fi

SPOT_BASE_URL="${SPOT_BASE_URL:-http://127.0.0.1:8787}"
FLEET_STATUS_FILE="${FLEET_STATUS_FILE:-/home/ogre/spot-stack/watch/state/fleet-status.json}"
NFS_LOG="${NFS_LOG:-/mnt/collective/logs/spot/worker-recover.jsonl}"
LOCAL_LOG="${LOCAL_LOG:-/home/ogre/spot-stack/watch/logs/worker-recover.jsonl}"
mkdir -p "$(dirname "$LOCAL_LOG")" 2>/dev/null || true
if mkdir -p "$(dirname "$NFS_LOG")" 2>/dev/null; then
  LOG_FILE="$NFS_LOG"
else
  LOG_FILE="$LOCAL_LOG"
fi
SSH_KEY="${SSH_KEY:-/root/.ssh/spot_fleet}"
SSH_USER="${SSH_USER:-ogre}"
SSH_OPTS="-i $SSH_KEY -o StrictHostKeyChecking=no -o ConnectTimeout=5 -o BatchMode=yes"
OLLAMA_PORT="${OLLAMA_PORT:-11434}"

mkdir -p "$(dirname "$LOG_FILE")" 2>/dev/null || true

log_json() {
  local event="$1"
  local extra="${2:-}"
  local ts
  ts="$(date -u +'%Y-%m-%dT%H:%M:%SZ')"
  if [[ -n "$extra" ]]; then
    printf '{"ts":"%s","worker":"%s","event":"%s",%s}\n' \
      "$ts" "$WORKER" "$event" "$extra" >> "$LOG_FILE" 2>/dev/null || true
  else
    printf '{"ts":"%s","worker":"%s","event":"%s"}\n' \
      "$ts" "$WORKER" "$event" >> "$LOG_FILE" 2>/dev/null || true
  fi
}

# Get worker IP from fleet status
get_worker_ip() {
  python3 - "$FLEET_STATUS_FILE" "$WORKER" <<'PY'
import json, sys
try:
    with open(sys.argv[1]) as f:
        data = json.load(f)
    hosts = data.get("hosts", {})
    info = hosts.get(sys.argv[2], {})
    # base_url not in fleet status but we can derive from cluster config
except Exception:
    pass
PY
}

# Get worker base_url from cluster config
get_worker_base_url() {
  python3 - /home/ogre/spot-stack/spot-core/config/cluster_config.json "$WORKER" <<'PY'
import json, sys
try:
    with open(sys.argv[1]) as f:
        data = json.load(f)
    url = data.get("workers", {}).get(sys.argv[2], {}).get("base_url", "")
    print(url)
except Exception:
    print("")
PY
}

BASE_URL="$(get_worker_base_url)"
if [[ -z "$BASE_URL" ]]; then
  log_json "recover_abort" '"reason":"worker_not_in_cluster_config"'
  echo "ERROR: $WORKER not found in cluster config" >&2
  exit 1
fi

# Extract host from base_url (http://192.168.10.13:11434 -> 192.168.10.13)
WORKER_HOST="$(echo "$BASE_URL" | sed 's|http://||' | cut -d: -f1)"

log_json "recover_start" "\"base_url\":\"$BASE_URL\",\"host\":\"$WORKER_HOST\""

# Step 1: Ping check
if ! ping -c 1 -W 3 "$WORKER_HOST" >/dev/null 2>&1; then
  log_json "recover_ping_fail" '"reason":"host_unreachable_icmp"'
  echo "FAIL: $WORKER host $WORKER_HOST not reachable via ping"
  exit 1
fi

log_json "recover_ping_ok"

# Step 2: SSH probe
if ! ssh $SSH_OPTS "${SSH_USER}@${WORKER_HOST}" "echo ok" >/dev/null 2>&1; then
  log_json "recover_ssh_fail" '"reason":"ssh_connection_refused_or_timeout"'
  echo "FAIL: $WORKER SSH not responding on $WORKER_HOST"
  exit 1
fi

log_json "recover_ssh_ok"

# Step 3: Check if ollama service is running via SSH
OLLAMA_STATUS="$(ssh $SSH_OPTS "${SSH_USER}@${WORKER_HOST}" \
  "systemctl is-active ollama 2>/dev/null || echo inactive" 2>/dev/null || echo "unknown")"

log_json "recover_service_check" "\"ollama_status\":\"$OLLAMA_STATUS\""

if [[ "$OLLAMA_STATUS" != "active" ]]; then
  # Step 4: Attempt service restart via spot-core API
  log_json "recover_restart_attempt" '"method":"spot_api"'

  RESTART_RESULT="$(curl -fsS --max-time 30 -X POST \
    "${SPOT_BASE_URL}/actions/restart-service/${WORKER}/ollama" 2>/dev/null || echo "{}")"

  RESTART_OK="$(echo "$RESTART_RESULT" | python3 -c \
    "import json,sys; d=json.load(sys.stdin); print('true' if d.get('ok') else 'false')" \
    2>/dev/null || echo "false")"

  if [[ "$RESTART_OK" != "true" ]]; then
    # Fallback: restart directly via SSH
    log_json "recover_restart_ssh_fallback"
    ssh $SSH_OPTS "${SSH_USER}@${WORKER_HOST}" \
      "sudo systemctl restart ollama 2>/dev/null || true" >/dev/null 2>&1 || true
    sleep 5
  else
    sleep 3
  fi
fi

# Step 5: Verify ollama API responds
OLLAMA_HEALTH="$(curl -fsS --connect-timeout 5 --max-time 10 \
  "http://${WORKER_HOST}:${OLLAMA_PORT}/api/tags" 2>/dev/null || echo "{}")"

OLLAMA_OK="$(echo "$OLLAMA_HEALTH" | python3 -c \
  "import json,sys; d=json.load(sys.stdin); print('true' if 'models' in d else 'false')" \
  2>/dev/null || echo "false")"

if [[ "$OLLAMA_OK" != "true" ]]; then
  log_json "recover_ollama_verify_fail" '"reason":"ollama_api_not_responding"'
  echo "FAIL: $WORKER SSH ok but ollama API not responding"
  exit 1
fi

log_json "recover_ollama_ok"

# Step 6: Verify spot-core sees the worker as healthy
sleep 2
READINESS="$(curl -fsS --max-time 10 "${SPOT_BASE_URL}/operator/readiness" 2>/dev/null || echo "{}")"
WORKER_OK="$(echo "$READINESS" | python3 -c "
import json, sys
d = json.load(sys.stdin)
workers = d.get('fleet', {}).get('workers', [])
for w in workers:
    if w.get('worker') == sys.argv[1]:
        print('true' if w.get('ok') else 'false')
        sys.exit(0)
print('unknown')
" "$WORKER" 2>/dev/null || echo "unknown")"

log_json "recover_complete" "\"ollama_ok\":true,\"spot_sees_worker\":\"$WORKER_OK\""

echo "OK: $WORKER recovered — SSH up, ollama responding, spot sees worker: $WORKER_OK"
exit 0
