#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="/home/ogre/spot-stack/watch"
STATE_DIR="${BASE_DIR}/state"
LOG_DIR="${BASE_DIR}/logs"
BACKUP_DIR="${BASE_DIR}/backups"
POLICY_FILE="${BASE_DIR}/fleet-policy.json"
REMEDIATION_STATE_FILE="${STATE_DIR}/remediation-state.json"
ROUTING_AUDIT_SUMMARY_FILE="${STATE_DIR}/routing-audit-summary.json"
FLEET_STATUS_FILE="${STATE_DIR}/fleet-status.json"
LOCAL_BACKUP_ROOT="${BACKUP_DIR}/remediation-state"
REMOTE_BACKUP_ROOT="/mnt/collective/fleet/backups/routing-remediation"

STAMP="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
EPOCH_NOW="$(date -u +%s)"
LOG_FILE="${LOG_DIR}/fleet-remediate.log"

mkdir -p "$STATE_DIR" "$LOG_DIR" "$BACKUP_DIR" "$LOCAL_BACKUP_ROOT"
[[ -f "$REMEDIATION_STATE_FILE" ]] || echo "{}" > "$REMEDIATION_STATE_FILE"
[[ -f "$POLICY_FILE" ]] || echo "{}" > "$POLICY_FILE"

log() {
  local msg="$1"
  echo "[$STAMP] $msg" | tee -a "$LOG_FILE"
}

json_escape() {
  python3 - <<'PY' "$1"
import json, sys
print(json.dumps(sys.argv[1]))
PY
}

backup_state() {
  local backup_root="$LOCAL_BACKUP_ROOT"
  if [[ -d /mnt/collective ]] && mountpoint -q /mnt/collective 2>/dev/null; then
    backup_root="$REMOTE_BACKUP_ROOT"
  fi

  mkdir -p "$backup_root"

  if [[ -f "$REMEDIATION_STATE_FILE" ]]; then
    cp "$REMEDIATION_STATE_FILE" "$backup_root/remediation-state-${EPOCH_NOW}.json"
    log "backup_saved path=${backup_root}/remediation-state-${EPOCH_NOW}.json"
  else
    log "backup_skipped remediation_state_missing"
  fi
}

get_policy_value() {
  local key="$1"
  local default_value="$2"
  python3 - <<'PY' "$POLICY_FILE" "$key" "$default_value"
import json, sys

policy_path = sys.argv[1]
key = sys.argv[2]
default = sys.argv[3]

try:
    with open(policy_path, "r", encoding="utf-8") as f:
        data = json.load(f)
except Exception:
    print(default)
    raise SystemExit(0)

cur = data
for part in key.split("."):
    if isinstance(cur, dict) and part in cur:
        cur = cur[part]
    else:
        print(default)
        raise SystemExit(0)

if isinstance(cur, bool):
    print(str(cur).lower())
elif cur is None:
    print(default)
else:
    print(cur)
PY
}

fetch_routing_audit() {
  local url="http://127.0.0.1:8787/stats/routing-audit?limit=${AUDIT_LIMIT}"
  if curl -fsS --max-time 5 "$url" > "${ROUTING_AUDIT_SUMMARY_FILE}.tmp"; then
    if jq empty "${ROUTING_AUDIT_SUMMARY_FILE}.tmp" >/dev/null 2>&1; then
      mv "${ROUTING_AUDIT_SUMMARY_FILE}.tmp" "$ROUTING_AUDIT_SUMMARY_FILE"
      return 0
    fi
  fi
  rm -f "${ROUTING_AUDIT_SUMMARY_FILE}.tmp"
  return 1
}

quarantine_worker() {
  local worker="$1"
  local reason="$2"
  local seconds="$3"

  local payload
  payload="$(curl -fsS -X POST "http://127.0.0.1:8787/quarantine/${worker}?seconds=${seconds}&reason=${reason}" 2>/dev/null || true)"

  if [[ -n "$payload" ]]; then
    log "quarantine_applied worker=${worker} seconds=${seconds} reason=${reason}"
    return 0
  fi

  log "quarantine_failed worker=${worker} seconds=${seconds} reason=${reason}"
  return 1
}

unquarantine_worker() {
  local worker="$1"

  local payload
  payload="$(curl -fsS -X DELETE "http://127.0.0.1:8787/quarantine/${worker}" 2>/dev/null || true)"

  if [[ -n "$payload" ]]; then
    log "quarantine_released worker=${worker}"
    return 0
  fi

  log "quarantine_release_failed worker=${worker}"
  return 1
}

restart_worker_service_via_api() {
  local worker="$1"
  local service="$2"
  local url="http://127.0.0.1:8787/actions/restart-service/${worker}/${service}"

  local payload
  if ! payload="$(curl -fsS --max-time 30 -X POST "$url" 2>/dev/null)"; then
    log "service_restart_api_failed worker=${worker} service=${service} reason=request_failed"
    return 1
  fi

  if ! jq empty >/dev/null 2>&1 <<<"$payload"; then
    log "service_restart_api_failed worker=${worker} service=${service} reason=invalid_json"
    return 1
  fi

  local ok restart_returncode remote_after backup_path action_log_path
  ok="$(jq -r '.ok // false' <<<"$payload")"
  restart_returncode="$(jq -r '
    .restart_returncode
    // .verification.restart_returncode
    // .result.restart_returncode
    // "null"
  ' <<<"$payload")"
  remote_after="$(jq -r '
    .remote_after
    // .verification.remote_after
    // .result.remote_after
    // "unknown"
  ' <<<"$payload")"
  backup_path="$(jq -r '
    .backup_path
    // .backup.path
    // .result.backup_path
    // ""
  ' <<<"$payload")"
  action_log_path="$(jq -r '
    .action_log_path
    // .log_path
    // .result.action_log_path
    // ""
  ' <<<"$payload")"

  if [[ "$ok" == "true" && "$restart_returncode" == "0" && "$remote_after" == "active" ]]; then
    log "service_restart_api_ok worker=${worker} service=${service} restart_returncode=${restart_returncode} remote_after=${remote_after} backup_path=${backup_path} action_log_path=${action_log_path}"
    return 0
  fi

  log "service_restart_api_failed worker=${worker} service=${service} ok=${ok} restart_returncode=${restart_returncode} remote_after=${remote_after} backup_path=${backup_path} action_log_path=${action_log_path}"
  return 1
}

service_down_workers_from_status() {
  local status_file="$1"
  python3 - "$status_file" <<'PY'
import json
import sys

path = sys.argv[1]

try:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
except Exception:
    raise SystemExit(0)

hosts = data.get("hosts", {})
if not isinstance(hosts, dict):
    raise SystemExit(0)

for worker, info in hosts.items():
    if not isinstance(info, dict):
        continue
    alerts = info.get("alerts", [])
    if not isinstance(alerts, list):
        alerts = []
    if "service_down" in alerts:
        print(worker)
PY
}

ENABLED="$(get_policy_value "routing_remediation.enabled" "true")"
AUDIT_LIMIT="$(get_policy_value "routing_remediation.audit_limit" "200")"
MIN_VIOLATIONS="$(get_policy_value "routing_remediation.min_violations" "1")"
QUARANTINE_SECONDS="$(get_policy_value "routing_remediation.quarantine_seconds" "1800")"
AUTO_UNQUARANTINE="$(get_policy_value "routing_remediation.auto_unquarantine" "true")"
FALLBACK_NOTE_THRESHOLD="$(get_policy_value "routing_remediation.fallback_note_threshold" "1")"
FALLBACK_DEGRADED_THRESHOLD="$(get_policy_value "routing_remediation.fallback_degraded_threshold" "3")"
FALLBACK_ESCALATE_THRESHOLD="$(get_policy_value "routing_remediation.fallback_escalate_threshold" "5")"
DEGRADED_CLEAR_RUNS="$(get_policy_value "routing_remediation.degraded_clear_runs" "2")"
DEGRADED_CLEAR_MAX_FALLBACKS="$(get_policy_value "routing_remediation.degraded_clear_max_fallbacks" "0")"
FALLBACK_RECENT_WINDOW_SEC="$(get_policy_value "routing_remediation.fallback_recent_window_sec" "120")"

SERVICE_REMEDIATION_ENABLED="$(get_policy_value "service_remediation.enabled" "true")"
SERVICE_REMEDIATION_TARGET_SERVICE="$(get_policy_value "service_remediation.target_service" "ollama")"

if [[ "$ENABLED" != "true" ]]; then
  log "remediation_disabled"
  exit 0
fi

if ! fetch_routing_audit; then
  log "routing_audit_fetch_failed"
  log "remediation_skipped_due_to_missing_audit"
  exit 0
fi

backup_state

TMP_UPDATED_STATE="$(mktemp)"

python3 - <<'PY' \
  "$ROUTING_AUDIT_SUMMARY_FILE" \
  "$REMEDIATION_STATE_FILE" \
  "$TMP_UPDATED_STATE" \
  "$EPOCH_NOW" \
  "$MIN_VIOLATIONS" \
  "$QUARANTINE_SECONDS" \
  "$AUTO_UNQUARANTINE" \
  "$FALLBACK_NOTE_THRESHOLD" \
  "$FALLBACK_DEGRADED_THRESHOLD" \
  "$FALLBACK_ESCALATE_THRESHOLD" \
  "$DEGRADED_CLEAR_RUNS" \
  "$DEGRADED_CLEAR_MAX_FALLBACKS" \
  "$FALLBACK_RECENT_WINDOW_SEC"
import json
import sys
from collections import defaultdict

audit_path = sys.argv[1]
state_path = sys.argv[2]
out_path = sys.argv[3]
now = int(sys.argv[4])
min_violations = int(sys.argv[5])
quarantine_seconds = int(sys.argv[6])
auto_unquarantine = sys.argv[7].lower() == "true"
fallback_note_threshold = int(sys.argv[8])
fallback_degraded_threshold = int(sys.argv[9])
fallback_escalate_threshold = int(sys.argv[10])
degraded_clear_runs = int(sys.argv[11])
degraded_clear_max_fallbacks = int(sys.argv[12])
fallback_recent_window_sec = int(sys.argv[13])

try:
    with open(audit_path, "r", encoding="utf-8") as f:
        audit = json.load(f)
except Exception:
    audit = {}

try:
    with open(state_path, "r", encoding="utf-8") as f:
        state = json.load(f)
except Exception:
    state = {}

if not isinstance(state, dict):
    state = {}

items = audit.get("items", [])
if not isinstance(items, list):
    items = []

fallbacks_by_worker = defaultdict(list)
recent_fallbacks_by_worker = defaultdict(list)

cutoff = now - fallback_recent_window_sec

for item in items:
    if not isinstance(item, dict):
        continue
    if item.get("route_class") != "fallback":
        continue

    worker = item.get("selected_worker") or item.get("final_worker")
    if not worker:
        continue

    fallbacks_by_worker[worker].append(item)

    ts = item.get("ts")
    if isinstance(ts, int) and ts >= cutoff:
        recent_fallbacks_by_worker[worker].append(item)

violations_by_worker = defaultdict(list)

for item in items:
    if not isinstance(item, dict):
        continue
    if item.get("route_class") != "violation":
        continue

    worker = item.get("selected_worker") or item.get("final_worker")
    if not worker:
        continue

    violations_by_worker[worker].append(item)

if "_meta" not in state or not isinstance(state.get("_meta"), dict):
    state["_meta"] = {}

state["_meta"]["last_run_ts"] = now
state["_meta"]["last_audit_window_count"] = int(audit.get("window_count", 0) or 0)
state["_meta"]["last_audit_violations"] = int(audit.get("violations", 0) or 0)

actions = {
    "quarantine": [],
    "release": [],
    "degraded": [],
    "escalated": [],
    "unchanged": [],
}

fresh_violations_by_worker = {}

for worker, entries in violations_by_worker.items():
    entry = state.get(worker, {})
    if not isinstance(entry, dict):
        entry = {}

    release_ts = int(entry.get("release_ts", 0) or 0)
    fresh_entries = []

    for item in entries:
        item_ts = int(item.get("ts", 0) or 0)
        if release_ts > 0 and item_ts <= release_ts:
            continue
        fresh_entries.append(item)

    if len(fresh_entries) < min_violations:
        continue

    fresh_violations_by_worker[worker] = fresh_entries

    last_violation_ts = max(int(item.get("ts", 0) or 0) for item in fresh_entries)
    reason = str(fresh_entries[0].get("violation_reason") or "routing_violation")
    until = now + quarantine_seconds
    already_quarantined = bool(entry.get("quarantined", False))

    entry.update(
        {
            "quarantined": True,
            "reason": f"routing_violation:{reason}",
            "since_ts": entry.get("since_ts", now if not already_quarantined else entry.get("since_ts", now)),
            "until_ts": until,
            "last_violation_ts": last_violation_ts,
            "violation_count_window": len(fresh_entries),
            "last_route_class": "violation",
            "last_updated_ts": now,
            "last_updated_by": "fleet-remediate.sh",
            "fallback_count_window": len(fallbacks_by_worker.get(worker, [])),
        }
    )
    state[worker] = entry

    actions["quarantine"].append(
        {
            "worker": worker,
            "reason": entry["reason"],
            "until_ts": until,
            "violation_count_window": len(fresh_entries),
            "already_quarantined": already_quarantined,
        }
    )

for worker, entry in list(state.items()):
    if worker == "_meta":
        continue
    if not isinstance(entry, dict):
        continue

    quarantined = bool(entry.get("quarantined", False))
    until_ts = int(entry.get("until_ts", 0) or 0)
    fallback_count = len(fallbacks_by_worker.get(worker, []))
    recent_fallback_count = len(recent_fallbacks_by_worker.get(worker, []))

    clean_runs = int(entry.get("degraded_clean_runs", 0) or 0)
    if recent_fallback_count <= degraded_clear_max_fallbacks:
        clean_runs += 1
    else:
        clean_runs = 0

    entry["degraded_clean_runs"] = clean_runs
    entry["recent_fallback_count_window"] = recent_fallback_count

    if recent_fallback_count >= fallback_note_threshold:
        entry["last_fallback_ts"] = now
        entry["fallback_count_window"] = fallback_count
        entry["last_route_class"] = "fallback"
        entry["last_updated_ts"] = now
        entry["last_updated_by"] = "fleet-remediate.sh"

        if recent_fallback_count >= fallback_degraded_threshold:
            entry["degraded"] = True
            entry["degraded_reason"] = f"routing_fallback_pressure:{recent_fallback_count}"
            actions["degraded"].append(
                {
                    "worker": worker,
                    "fallback_count_window": fallback_count,
                    "reason": "fallback_pressure",
                }
            )

        if recent_fallback_count >= fallback_escalate_threshold:
            actions["escalated"].append(
                {
                    "worker": worker,
                    "fallback_count_window": fallback_count,
                    "reason": "fallback_pressure_high",
                }
            )

        if recent_fallback_count < fallback_degraded_threshold:
            actions["unchanged"].append(
                {
                    "worker": worker,
                    "reason": "fallback_detected",
                    "fallback_count_window": fallback_count,
                }
            )

        state[worker] = entry

    elif entry.get("degraded") is True:
        if clean_runs >= degraded_clear_runs:
            entry["degraded"] = False
            entry["degraded_reason"] = ""
            entry["fallback_count_window"] = fallback_count
            entry["last_updated_ts"] = now
            entry["last_updated_by"] = "fleet-remediate.sh"
            state[worker] = entry

            actions["release"].append(
                {
                    "worker": worker,
                    "reason": "degraded_cleared",
                }
            )
        else:
            state[worker] = entry

    if quarantined:
        if worker in fresh_violations_by_worker:
            actions["unchanged"].append(
                {
                    "worker": worker,
                    "reason": "still_has_fresh_violation_in_window",
                    "quarantined": True,
                }
            )
            continue

        if auto_unquarantine and until_ts > 0 and now >= until_ts:
            entry["quarantined"] = False
            entry["release_ts"] = now
            entry["last_updated_ts"] = now
            entry["last_updated_by"] = "fleet-remediate.sh"
            state[worker] = entry
            actions["release"].append({"worker": worker})
        else:
            actions["unchanged"].append(
                {
                    "worker": worker,
                    "reason": "quarantine_not_expired_or_auto_release_disabled",
                    "quarantined": True,
                    "until_ts": until_ts,
                }
            )

result = {
    "state": state,
    "actions": actions,
}

with open(out_path, "w", encoding="utf-8") as f:
    json.dump(result, f, indent=2, sort_keys=True)
PY

QUARANTINE_COUNT="$(jq '.actions.quarantine | length' "$TMP_UPDATED_STATE")"
if [[ "$QUARANTINE_COUNT" -gt 0 ]]; then
  while IFS= read -r row; do
    worker="$(jq -r '.worker' <<<"$row")"
    reason="$(jq -r '.reason' <<<"$row")"
    already_quarantined="$(jq -r '.already_quarantined' <<<"$row")"
    if [[ "$already_quarantined" == "true" ]]; then
      log "quarantine_already_present worker=${worker} reason=${reason}"
      continue
    fi
    quarantine_worker "$worker" "$reason" "$QUARANTINE_SECONDS" || true
  done < <(jq -c '.actions.quarantine[]' "$TMP_UPDATED_STATE")
fi

RELEASE_COUNT="$(jq '.actions.release | length' "$TMP_UPDATED_STATE")"
if [[ "$RELEASE_COUNT" -gt 0 ]]; then
  while IFS= read -r row; do
    worker="$(jq -r '.worker' <<<"$row")"
    unquarantine_worker "$worker" || true
  done < <(jq -c '.actions.release[]' "$TMP_UPDATED_STATE")
fi

jq '.state' "$TMP_UPDATED_STATE" > "${REMEDIATION_STATE_FILE}.tmp"
command mv -f "${REMEDIATION_STATE_FILE}.tmp" "$REMEDIATION_STATE_FILE"

SERVICE_RESTARTS_ATTEMPTED=0
SERVICE_RESTARTS_SUCCEEDED=0

if [[ "$SERVICE_REMEDIATION_ENABLED" == "true" ]]; then
  if [[ -f "$FLEET_STATUS_FILE" ]]; then
    while IFS= read -r worker; do
      [[ -n "$worker" ]] || continue
      SERVICE_RESTARTS_ATTEMPTED=$((SERVICE_RESTARTS_ATTEMPTED + 1))
      if restart_worker_service_via_api "$worker" "$SERVICE_REMEDIATION_TARGET_SERVICE"; then
        SERVICE_RESTARTS_SUCCEEDED=$((SERVICE_RESTARTS_SUCCEEDED + 1))
      fi
    done < <(service_down_workers_from_status "$FLEET_STATUS_FILE")
  else
    log "service_remediation_skipped reason=fleet_status_missing path=${FLEET_STATUS_FILE}"
  fi
else
  log "service_remediation_disabled"
fi

python3 - <<'PY' "$TMP_UPDATED_STATE" "$SERVICE_RESTARTS_ATTEMPTED" "$SERVICE_RESTARTS_SUCCEEDED"
import json, sys

with open(sys.argv[1], "r", encoding="utf-8") as f:
    data = json.load(f)

service_restarts_attempted = int(sys.argv[2])
service_restarts_succeeded = int(sys.argv[3])

q = data.get("actions", {}).get("quarantine", [])
r = data.get("actions", {}).get("release", [])
d = data.get("actions", {}).get("degraded", [])
e = data.get("actions", {}).get("escalated", [])
u = data.get("actions", {}).get("unchanged", [])

parts = []
if q:
    parts.append("quarantine=" + ",".join(sorted(item["worker"] for item in q)))
if r:
    parts.append("release=" + ",".join(sorted(item["worker"] for item in r)))
if d:
    parts.append("degraded=" + ",".join(sorted(item["worker"] for item in d)))
if e:
    parts.append("escalated=" + ",".join(sorted(item["worker"] for item in e)))
if service_restarts_attempted:
    parts.append(f"service_restarts={service_restarts_succeeded}/{service_restarts_attempted}")
if not parts:
    parts.append("no_remediation_changes")

print("REMEDIATE " + " | ".join(parts) + f" | unchanged={len(u)}")
PY

rm -f "$TMP_UPDATED_STATE"
