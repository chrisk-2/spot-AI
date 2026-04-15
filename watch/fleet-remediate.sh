#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="/home/ogre/spot-stack/watch"
STATE_FILE="${BASE_DIR}/state/fleet-status.json"
STATE_TRACK_FILE="${BASE_DIR}/state/remediation-state.json"
LOG_DIR="${BASE_DIR}/logs"
LOG_FILE="${LOG_DIR}/fleet-remediate.log"
BACKUP_DIR="${BASE_DIR}/backups/remediation"

COOLDOWN_SECONDS=900
MAX_RETRIES=3

mkdir -p "$LOG_DIR" "$BACKUP_DIR" "${BASE_DIR}/state"
[[ -f "$STATE_TRACK_FILE" ]] || echo "{}" > "$STATE_TRACK_FILE"

STAMP="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
RUN_DIR="${BACKUP_DIR}/${STAMP}"
mkdir -p "$RUN_DIR"

log() {
  echo "[$STAMP] $*" | tee -a "$LOG_FILE"
}

ssh_quick() {
  local host="$1"
  shift
  ssh -o BatchMode=yes -o ConnectTimeout=5 "$host" "$@"
}

[[ -f "$STATE_FILE" ]] || {
  log "no state file found"
  exit 0
}

TARGETS_FILE="$(mktemp)"
trap 'rm -f "$TARGETS_FILE"' EXIT

python3 - <<'PY' "$STATE_FILE" > "$TARGETS_FILE"
import json, sys

with open(sys.argv[1], "r", encoding="utf-8") as f:
    data = json.load(f)

for host, info in data.get("hosts", {}).items():
    alerts = info.get("alerts", [])
    if "service_down" in alerts and host.startswith("spot-worker-"):
        print(host)
PY

while read -r host; do
  [[ -n "$host" ]] || continue

  NOW="$(date +%s)"

  read -r LAST_RUN RETRIES QUARANTINED <<< "$(python3 - <<'PY' "$STATE_TRACK_FILE" "$host"
import json, sys

with open(sys.argv[1], "r", encoding="utf-8") as f:
    data = json.load(f)

host = sys.argv[2]
entry = data.get(host, {})

# Backward compatibility: old format stored just an int timestamp
if isinstance(entry, int):
    last_run = entry
    retries = 0
    quarantined = False
elif isinstance(entry, dict):
    last_run = int(entry.get("last_run", 0))
    retries = int(entry.get("retries", 0))
    quarantined = bool(entry.get("quarantined", False))
else:
    last_run = 0
    retries = 0
    quarantined = False

print(last_run, retries, quarantined)
PY
)"

  if [[ "$QUARANTINED" == "True" ]]; then
    log "host $host is quarantined — skipping"
    continue
  fi

  if (( NOW - LAST_RUN < COOLDOWN_SECONDS )); then
    REMAINING=$(( COOLDOWN_SECONDS - (NOW - LAST_RUN) ))
    log "cooldown active for $host (${REMAINING}s remaining) — skipping"
    continue
  fi

  log "pre-backup for $host"
  ssh_quick "$host" "systemctl status ollama --no-pager -l" \
    > "${RUN_DIR}/${host}-ollama-status-before.txt" 2>&1 || true
  ssh_quick "$host" "journalctl -u ollama -n 100 --no-pager" \
    > "${RUN_DIR}/${host}-ollama-journal-before.txt" 2>&1 || true

  log "restarting ollama on $host"
  if ssh_quick "$host" "sudo systemctl restart ollama"; then
    sleep 5

    if ssh_quick "$host" "systemctl is-active ollama" >/dev/null 2>&1; then
      log "restart succeeded on $host"

      python3 - <<'PY' "$STATE_TRACK_FILE" "$host" "$NOW"
import json, sys

path = sys.argv[1]
host = sys.argv[2]
ts = int(sys.argv[3])

with open(path, "r", encoding="utf-8") as f:
    data = json.load(f)

data[host] = {
    "last_run": ts,
    "retries": 0,
    "quarantined": False
}

with open(path, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, sort_keys=True)
PY
    else
      log "restart did not recover $host"

      NEW_RETRIES=$(( RETRIES + 1 ))

      if (( NEW_RETRIES >= MAX_RETRIES )); then
        log "QUARANTINE $host after $NEW_RETRIES failed recoveries"

        python3 - <<'PY' "$STATE_TRACK_FILE" "$host" "$NOW" "$NEW_RETRIES"
import json, sys

path = sys.argv[1]
host = sys.argv[2]
ts = int(sys.argv[3])
retries = int(sys.argv[4])

with open(path, "r", encoding="utf-8") as f:
    data = json.load(f)

data[host] = {
    "last_run": ts,
    "retries": retries,
    "quarantined": True
}

with open(path, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, sort_keys=True)
PY
      else
        log "restart failed verification on $host (retry ${NEW_RETRIES}/${MAX_RETRIES})"

        python3 - <<'PY' "$STATE_TRACK_FILE" "$host" "$NOW" "$NEW_RETRIES"
import json, sys

path = sys.argv[1]
host = sys.argv[2]
ts = int(sys.argv[3])
retries = int(sys.argv[4])

with open(path, "r", encoding="utf-8") as f:
    data = json.load(f)

data[host] = {
    "last_run": ts,
    "retries": retries,
    "quarantined": False
}

with open(path, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, sort_keys=True)
PY
      fi
    fi
  else
    log "restart command failed on $host"

    NEW_RETRIES=$(( RETRIES + 1 ))

    if (( NEW_RETRIES >= MAX_RETRIES )); then
      log "QUARANTINE $host after $NEW_RETRIES restart command failures"

      python3 - <<'PY' "$STATE_TRACK_FILE" "$host" "$NOW" "$NEW_RETRIES"
import json, sys

path = sys.argv[1]
host = sys.argv[2]
ts = int(sys.argv[3])
retries = int(sys.argv[4])

with open(path, "r", encoding="utf-8") as f:
    data = json.load(f)

data[host] = {
    "last_run": ts,
    "retries": retries,
    "quarantined": True
}

with open(path, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, sort_keys=True)
PY
    else
      python3 - <<'PY' "$STATE_TRACK_FILE" "$host" "$NOW" "$NEW_RETRIES"
import json, sys

path = sys.argv[1]
host = sys.argv[2]
ts = int(sys.argv[3])
retries = int(sys.argv[4])

with open(path, "r", encoding="utf-8") as f:
    data = json.load(f)

data[host] = {
    "last_run": ts,
    "retries": retries,
    "quarantined": False
}

with open(path, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, sort_keys=True)
PY
    fi
  fi

done < "$TARGETS_FILE"
