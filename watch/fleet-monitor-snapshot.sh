#!/usr/bin/env bash
set -Eeuo pipefail

BASE_DIR="${BASE_DIR:-/home/ogre/spot-stack/watch}"
STATE_DIR="${STATE_DIR:-${BASE_DIR}/state}"
LOG_DIR="${LOG_DIR:-${BASE_DIR}/logs}"
SPOT_OPS="${SPOT_OPS:-${BASE_DIR}/spot-ops.sh}"
HISTORY_DIR="${HISTORY_DIR:-${STATE_DIR}/history}"
SNAPSHOT_DIR="${SNAPSHOT_DIR:-${HISTORY_DIR}/snapshots}"
SUMMARY_JSONL="${SUMMARY_JSONL:-${HISTORY_DIR}/monitor-summary.jsonl}"
DEFAULT_DNS_QUERY="${DEFAULT_DNS_QUERY:-google.com}"

mkdir -p "$STATE_DIR" "$LOG_DIR" "$HISTORY_DIR" "$SNAPSHOT_DIR"

need_cmd() {
  local cmd="$1"
  command -v "$cmd" >/dev/null 2>&1 || {
    echo "ERROR: required command not found: $cmd" >&2
    exit 2
  }
}

need_file() {
  local file="$1"
  [[ -f "$file" ]] || {
    echo "ERROR: required file not found: $file" >&2
    exit 2
  }
}

log() {
  printf '%s %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*"
}

capture_json_command() {
  local label="$1"
  shift
  local raw
  if ! raw="$($@)"; then
    echo "ERROR: command failed for ${label}" >&2
    return 1
  fi

  printf '%s\n' "$raw" | awk 'BEGIN{capture=0} /^\{/ {capture=1} capture {print}'
}

main() {
  need_cmd jq
  need_cmd python3
  need_file "$SPOT_OPS"

  local stamp epoch day snapshot_file tmp_file
  stamp="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  epoch="$(date -u +%s)"
  day="$(date -u +%Y-%m-%d)"
  snapshot_file="${SNAPSHOT_DIR}/${day}-${epoch}.json"
  tmp_file="$(mktemp)"

  local quick_health_json dns_latency_json net_latency_json
  quick_health_json="$(capture_json_command quick-health "$SPOT_OPS" quick-health)"
  dns_latency_json="$(capture_json_command dns-latency "$SPOT_OPS" dns-latency "$DEFAULT_DNS_QUERY")"
  net_latency_json="$(capture_json_command net-latency "$SPOT_OPS" net-latency)"

  jq -n \
    --arg timestamp "$stamp" \
    --argjson quick_health "$quick_health_json" \
    --argjson dns_latency "$dns_latency_json" \
    --argjson net_latency "$net_latency_json" \
    '{
      timestamp: $timestamp,
      quick_health: $quick_health,
      dns_latency: $dns_latency,
      net_latency: $net_latency
    }' > "$tmp_file"

  mv "$tmp_file" "$snapshot_file"

  jq -c '{
    timestamp,
    health_ok: (.quick_health.health.ok // false),
    routing_ok: (.quick_health.routing_audit.ok // false),
    routing_violations: (.quick_health.routing_audit.violations // 0),
    routing_fallbacks: (.quick_health.routing_audit.fallbacks // 0),
    worker_ok_count: ((.quick_health.workers // []) | map(select(.ok == true)) | length),
    worker_fail_count: ((.quick_health.workers // []) | map(select(.ok != true)) | length),
    endpoint_ok_count: (.quick_health.endpoints.ok_count // 0),
    endpoint_fail_count: (.quick_health.endpoints.fail_count // 0),
    dns_ok_count: (.dns_latency.summary.ok_count // 0),
    dns_fail_count: (.dns_latency.summary.fail_count // 0),
    dns_cold_ms: ((.dns_latency.items // []) | map({key: .name, value: (.cold_ms // null)}) | from_entries),
    dns_warm_ms: ((.dns_latency.items // []) | map({key: .name, value: (.warm_ms // null)}) | from_entries),
    net_ok_count: (.net_latency.summary.ok_count // 0),
    net_fail_count: (.net_latency.summary.fail_count // 0),
    net_avg_ms: ((.net_latency.items // []) | map({key: .name, value: (.avg_ms // null)}) | from_entries),
    net_loss_pct: ((.net_latency.items // []) | map({key: .name, value: (.packet_loss_pct // null)}) | from_entries),
    snapshot_file: $snapshot_file
  }' --arg snapshot_file "$snapshot_file" "$snapshot_file" >> "$SUMMARY_JSONL"

  log "OK monitor snapshot written: $snapshot_file"
  jq '{
    timestamp,
    health_ok: (.quick_health.health.ok // false),
    routing_ok: (.quick_health.routing_audit.ok // false),
    worker_fail_count: ((.quick_health.workers // []) | map(select(.ok != true)) | length),
    endpoint_fail_count: (.quick_health.endpoints.fail_count // 0),
    dns_fail_count: (.dns_latency.summary.fail_count // 0),
    net_fail_count: (.net_latency.summary.fail_count // 0),
    snapshot_file: $snapshot_file
  }' --arg snapshot_file "$snapshot_file" "$snapshot_file"
}

main "$@"
