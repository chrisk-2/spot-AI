#!/usr/bin/env bash
# spot-worker-recover-loop.sh
set -euo pipefail

FLEET_STATUS="${FLEET_STATUS:-/home/ogre/spot-stack/watch/state/fleet-status.json}"
RECOVER_SCRIPT="${RECOVER_SCRIPT:-/home/ogre/spot-stack/watch/spot-worker-recover.sh}"
COOLDOWN_FILE="${COOLDOWN_FILE:-/home/ogre/spot-stack/watch/state/recover-cooldown.json}"
COOLDOWN_SECONDS="${COOLDOWN_SECONDS:-600}"
NFS_LOG="${NFS_LOG:-/mnt/collective/logs/spot/worker-recover.jsonl}"
LOCAL_LOG="${LOCAL_LOG:-/home/ogre/spot-stack/watch/logs/worker-recover.jsonl}"

mkdir -p "$(dirname "$LOCAL_LOG")" "$(dirname "$COOLDOWN_FILE")"
[[ -f "$COOLDOWN_FILE" ]] || echo '{}' > "$COOLDOWN_FILE"

# Use NFS log if mounted, fall back to local
if mkdir -p "$(dirname "$NFS_LOG")" 2>/dev/null; then
  LOG_FILE="$NFS_LOG"
else
  LOG_FILE="$LOCAL_LOG"
fi

now="$(date -u +%s)"

log() {
  printf '{"ts":"%s","event":"%s","detail":"%s"}\n' \
    "$(date -u +'%Y-%m-%dT%H:%M:%SZ')" "$1" "${2:-}" | tee -a "$LOG_FILE" 2>/dev/null || true
}

SSH_DOWN_WORKERS="$(python3 - "$FLEET_STATUS" <<'PY'
import json, sys
try:
    d = json.load(open(sys.argv[1]))
    for w, info in d.get("hosts", {}).items():
        if isinstance(info, dict) and "ssh_down" in info.get("alerts", []):
            print(w)
except Exception:
    pass
PY
)"

if [[ -z "$SSH_DOWN_WORKERS" ]]; then
  echo "No ssh_down workers."
  exit 0
fi

while IFS= read -r worker; do
  [[ -z "$worker" ]] && continue

  last_attempt="$(python3 -c "
import json
d = json.load(open('$COOLDOWN_FILE'))
print(d.get('$worker', {}).get('last_attempt_ts', 0))
" 2>/dev/null || echo 0)"

  age=$(( now - last_attempt ))
  if [[ "$age" -lt "$COOLDOWN_SECONDS" ]]; then
    remaining=$(( COOLDOWN_SECONDS - age ))
    log "recover_cooldown_skip" "$worker cooldown ${remaining}s remaining"
    echo "SKIP: $worker in cooldown (${remaining}s remaining)"
    continue
  fi

  echo "Attempting recovery: $worker"
  log "recover_attempt_start" "$worker"

  bash /home/ogre/spot-stack/watch/spot-wake.sh "$worker" 2>/dev/null || true
  sleep 45

  python3 - "$COOLDOWN_FILE" "$worker" "$now" << 'PY'
import json, sys
path, worker, ts = sys.argv[1], sys.argv[2], int(sys.argv[3])
try:
    d = json.load(open(path))
except Exception:
    d = {}
d.setdefault(worker, {})["last_attempt_ts"] = ts
json.dump(d, open(path, "w"), indent=2)
PY

  set +e
  bash "$RECOVER_SCRIPT" "$worker"
  rc=$?
  set -e

  if [[ "$rc" -eq 0 ]]; then
    log "recover_success" "$worker"
    echo "RECOVERED: $worker"
    python3 - "$COOLDOWN_FILE" "$worker" << 'PY'
import json, sys
path, worker = sys.argv[1], sys.argv[2]
try:
    d = json.load(open(path))
    d.pop(worker, None)
    json.dump(d, open(path, "w"), indent=2)
except Exception:
    pass
PY
  else
    log "recover_fail" "$worker exit_code=$rc"
    echo "FAILED: $worker (will retry after cooldown)"
  fi

done <<< "$SSH_DOWN_WORKERS"
