#!/usr/bin/env bash
set -u

STATE_DIR="$HOME/spot-stack/watch/state"
LOG_DIR="$HOME/spot-stack/watch/logs"
HEALTH_URL="http://127.0.0.1:8787/health"
REFRESH="${1:-3}"

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "Missing required command: $1"
    exit 1
  }
}

need_cmd curl
need_cmd jq

while true; do
  clear
  echo "=== SPOT FLEET DASHBOARD ========================================="
  echo "Time: $(date)"
  echo

  echo "[CORE HEALTH]"
  curl -fsS "$HEALTH_URL" 2>/dev/null | jq . 2>/dev/null || echo "spot-core not responding"
  echo

  echo "[FLEET STATUS]"
  if [[ -f "$STATE_DIR/fleet-status.json" ]]; then
    jq -r '
  if .hosts == null then
    "No fleet data"
  else
    .hosts | to_entries[] |
    .key as $name |
    .value |
    "- " + $name + ": " +
    (if .quarantined then "QUARANTINED"
     elif .eligible then "OK"
     else "INACTIVE" end)
  end
' "$STATE_DIR/fleet-status.json" 2>/dev/null

echo "[SUMMARY]"

jq -r '
  if has("hosts") then
    .hosts as $h |
    "Healthy: " + (
      [$h[] | select(.eligible == true and .quarantined == false)] | length | tostring
    ) + "\nQuarantined: " + (
      [$h[] | select(.quarantined == true)] | length | tostring
    )
  else
    "No data"
  end
' "$STATE_DIR/fleet-status.json" 2>/dev/null

  else
    echo "No fleet-status.json found"
  fi
  echo

  echo "[ROUTING SUMMARY]"
  if [[ -f "$STATE_DIR/routing-audit-summary.json" ]]; then
    jq . "$STATE_DIR/routing-audit-summary.json" 2>/dev/null || cat "$STATE_DIR/routing-audit-summary.json"
  else
    echo "No routing-audit-summary.json found"
  fi
  echo

  echo "[RECENT ROUTING AUDIT]"
  if [[ -f "$STATE_DIR/routing-audit.jsonl" ]]; then
    tail -n 10 "$STATE_DIR/routing-audit.jsonl"
  else
    echo "No routing-audit.jsonl found"
  fi
  echo

  echo "[RECENT LOG TAILS]"
  [[ -f "$LOG_DIR/fleet-watch.log" ]] && echo "-- fleet-watch.log --" && tail -n 5 "$LOG_DIR/fleet-watch.log"
  [[ -f "$LOG_DIR/fleet-remediate.log" ]] && echo "-- fleet-remediate.log --" && tail -n 5 "$LOG_DIR/fleet-remediate.log"
  echo
  echo "Refresh: ${REFRESH}s   Exit: Ctrl+C"
  sleep "$REFRESH"
done
