#!/usr/bin/env bash
set -Eeuo pipefail

BASE_DIR="${BASE_DIR:-/home/ogre/spot-stack/watch}"
STATE_DIR="${STATE_DIR:-${BASE_DIR}/state}"
LOG_DIR="${LOG_DIR:-${BASE_DIR}/logs}"
SPOT_BASE_URL="${SPOT_BASE_URL:-http://127.0.0.1:8787}"

VALIDATOR="${VALIDATOR:-${BASE_DIR}/fleet-validate.sh}"
FLEET_STATUS_FILE="${FLEET_STATUS_FILE:-${STATE_DIR}/fleet-status.json}"
AUDIT_SUMMARY_FILE="${AUDIT_SUMMARY_FILE:-${STATE_DIR}/routing-audit-summary.json}"
AUDIT_FILE="${AUDIT_FILE:-${STATE_DIR}/routing-audit.jsonl}"
WATCH_LOG_FILE="${WATCH_LOG_FILE:-${LOG_DIR}/fleet-watch.log}"
REMEDIATE_LOG_FILE="${REMEDIATE_LOG_FILE:-${LOG_DIR}/fleet-remediate.log}"

DEFAULT_LOG_LINES="${DEFAULT_LOG_LINES:-80}"
CURL_TIMEOUT="${CURL_TIMEOUT:-20}"

usage() {
  cat <<EOF
Usage: $(basename "$0") <command> [args]

Operator commands:
  validate                 Run scripted fleet validation
  smoke [worker]           Run validation with quarantine/unquarantine smoke test
  health                   Show /health, fleet-status.json, and /fleet/ping summary
  routing                  Show routing ownership and scheduler routing state
  audit [limit]            Show routing audit summary and recent items
  quarantine <worker> [seconds] [reason]
                           Quarantine a worker through spot-core API
  release <worker>         Release a quarantined worker through spot-core API
  logs [watch|remediate|both] [lines]
                           Tail or print recent operator logs

Environment overrides:
  BASE_DIR
  STATE_DIR
  LOG_DIR
  SPOT_BASE_URL
  VALIDATOR
  FLEET_STATUS_FILE
  AUDIT_SUMMARY_FILE
  AUDIT_FILE
  WATCH_LOG_FILE
  REMEDIATE_LOG_FILE
  DEFAULT_LOG_LINES
  CURL_TIMEOUT

Examples:
  $(basename "$0") validate
  $(basename "$0") smoke
  $(basename "$0") smoke spot-worker-01
  $(basename "$0") health
  $(basename "$0") routing
  $(basename "$0") audit
  $(basename "$0") audit 25
  $(basename "$0") quarantine spot-worker-03 1800 manual_test
  $(basename "$0") release spot-worker-03
  $(basename "$0") logs both 100
EOF
}

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

need_http() {
  need_cmd curl
  local endpoint="$1"
  curl -fsS --connect-timeout 5 --max-time "$CURL_TIMEOUT" "${SPOT_BASE_URL}${endpoint}" >/dev/null
}

json_pp() {
  local src="$1"
  if [[ -f "$src" ]]; then
    jq . "$src"
  else
    printf '%s\n' "$src" | jq .
  fi
}

api_get() {
  local endpoint="$1"
  curl -fsS --connect-timeout 5 --max-time "$CURL_TIMEOUT" "${SPOT_BASE_URL}${endpoint}"
}

api_post() {
  local endpoint="$1"
  curl -fsS -X POST --connect-timeout 5 --max-time "$CURL_TIMEOUT" "${SPOT_BASE_URL}${endpoint}"
}

api_delete() {
  local endpoint="$1"
  curl -fsS -X DELETE --connect-timeout 5 --max-time "$CURL_TIMEOUT" "${SPOT_BASE_URL}${endpoint}"
}

print_header() {
  printf '\n=== %s ===\n' "$1"
}

cmd_validate() {
  need_cmd bash
  need_file "$VALIDATOR"
  bash "$VALIDATOR"
}

cmd_smoke() {
  need_cmd bash
  need_file "$VALIDATOR"
  local worker="${1:-spot-worker-01}"
  bash "$VALIDATOR" --smoke --worker "$worker"
}

cmd_health() {
  need_cmd jq
  need_http "/health"

  print_header "spot-core /health"
  api_get "/health" | jq .

  print_header "fleet-status.json"
  if [[ -f "$FLEET_STATUS_FILE" ]]; then
    jq '{
      timestamp,
      core_health,
      routing_audit: {
        ok: .routing_audit.ok,
        primaries: .routing_audit.primaries,
        fallbacks: .routing_audit.fallbacks,
        violations: .routing_audit.violations,
        manual_overrides: .routing_audit.manual_overrides,
        window_count: .routing_audit.window_count,
        last_violation_ts: .routing_audit.last_violation_ts
      },
      hosts: (
        .hosts
        | to_entries
        | map({
            host: .key,
            ssh_ok: .value.ssh_ok,
            service_ok: .value.service_ok,
            quarantined: .value.quarantined,
            eligible: .value.eligible,
            alerts: .value.alerts,
            running_jobs: .value.running_jobs,
            load_1: .value.load_1,
            gpu_free_mb_max: .value.gpu_free_mb_max
          })
      )
    }' "$FLEET_STATUS_FILE"
  else
    echo "WARN: missing $FLEET_STATUS_FILE"
  fi

  print_header "spot-core /fleet/ping"
  api_get "/fleet/ping" | jq 'to_entries | map({
    worker: .key,
    ok: .value.ok,
    reason: .value.reason,
    primary_role: .value.primary_role,
    secondary_roles: .value.secondary_roles,
    quarantined: .value.quarantined,
    eligible: .value.eligible,
    alerts: .value.alerts,
    running_jobs: .value.running_jobs,
    watcher_running_jobs: .value.watcher_running_jobs
  })'
}

cmd_routing() {
  need_cmd jq
  need_http "/routing"

  print_header "role ownership"
  api_get "/routing" | jq '{
    role_owners,
    role_priority,
    priority_order,
    queue_policy,
    retry_policy,
    active_requests,
    active_gpu_requests,
    active_model_requests,
    waiting_requests,
    penalty_box
  }'
}

cmd_audit() {
  need_cmd jq
  local limit="${1:-20}"

  print_header "spot-core /stats/routing-audit"
  api_get "/stats/routing-audit?limit=${limit}" | jq '{
    ok,
    window_count,
    primaries,
    fallbacks,
    violations,
    manual_overrides,
    last_violation_ts,
    role_owners,
    by_role,
    items
  }'

  print_header "routing-audit-summary.json"
  if [[ -f "$AUDIT_SUMMARY_FILE" ]]; then
    jq . "$AUDIT_SUMMARY_FILE"
  else
    echo "WARN: missing $AUDIT_SUMMARY_FILE"
  fi

  print_header "routing-audit.jsonl tail"
  if [[ -f "$AUDIT_FILE" ]]; then
    tail -n "${limit}" "$AUDIT_FILE" | jq -R 'fromjson?'
  else
    echo "WARN: missing $AUDIT_FILE"
  fi
}

cmd_quarantine() {
  need_cmd jq
  local worker="${1:-}"
  local seconds="${2:-1800}"
  local reason="${3:-manual_quarantine}"

  [[ -n "$worker" ]] || {
    echo "ERROR: worker is required" >&2
    usage
    exit 2
  }

  print_header "quarantine ${worker}"
  api_post "/quarantine/${worker}?seconds=${seconds}&reason=${reason}" | jq .
}

cmd_release() {
  need_cmd jq
  local worker="${1:-}"

  [[ -n "$worker" ]] || {
    echo "ERROR: worker is required" >&2
    usage
    exit 2
  }

  print_header "release ${worker}"
  api_delete "/quarantine/${worker}" | jq .
}

show_log_block() {
  local label="$1"
  local file="$2"
  local lines="$3"

  print_header "${label} (${file})"
  if [[ -f "$file" ]]; then
    tail -n "$lines" "$file"
  else
    echo "WARN: missing $file"
  fi
}

cmd_logs() {
  local which="${1:-both}"
  local lines="${2:-$DEFAULT_LOG_LINES}"

  case "$which" in
    watch)
      show_log_block "fleet-watch.log" "$WATCH_LOG_FILE" "$lines"
      ;;
    remediate)
      show_log_block "fleet-remediate.log" "$REMEDIATE_LOG_FILE" "$lines"
      ;;
    both)
      show_log_block "fleet-watch.log" "$WATCH_LOG_FILE" "$lines"
      show_log_block "fleet-remediate.log" "$REMEDIATE_LOG_FILE" "$lines"
      ;;
    *)
      echo "ERROR: invalid logs target: $which" >&2
      usage
      exit 2
      ;;
  esac
}

main() {
  local cmd="${1:-}"
  shift || true

  case "$cmd" in
    validate)   cmd_validate "$@" ;;
    smoke)      cmd_smoke "$@" ;;
    health)     cmd_health "$@" ;;
    routing)    cmd_routing "$@" ;;
    audit)      cmd_audit "$@" ;;
    quarantine) cmd_quarantine "$@" ;;
    release)    cmd_release "$@" ;;
    logs)       cmd_logs "$@" ;;
    -h|--help|"") usage ;;
    *)
      echo "ERROR: unknown command: $cmd" >&2
      usage
      exit 2
      ;;
  esac
}

main "$@"
