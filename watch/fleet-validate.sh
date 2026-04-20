#!/usr/bin/env bash
set -Eeuo pipefail

SPOT_BASE_URL="${SPOT_BASE_URL:-http://127.0.0.1:8787}"
WATCH_STATE_DIR="${WATCH_STATE_DIR:-/home/ogre/spot-stack/watch/state}"
AUDIT_FILE="${AUDIT_FILE:-${WATCH_STATE_DIR}/routing-audit.jsonl}"
FLEET_STATUS_FILE="${FLEET_STATUS_FILE:-${WATCH_STATE_DIR}/fleet-status.json}"
AUDIT_SUMMARY_FILE="${AUDIT_SUMMARY_FILE:-${WATCH_STATE_DIR}/routing-audit-summary.json}"
SMOKE_WORKER="${SMOKE_WORKER:-spot-worker-01}"
CURL_TIMEOUT="${CURL_TIMEOUT:-30}"
POLL_INTERVAL="${POLL_INTERVAL:-2}"
POLL_ATTEMPTS="${POLL_ATTEMPTS:-15}"

SMOKE_MODE=0
VERBOSE=0

usage() {
  cat <<USAGE
Usage: $(basename "$0") [--smoke] [--worker <name>] [--base-url <url>] [--watch-state-dir <dir>] [--verbose]

Checks:
  1. role ownership routing:
     - general -> spot-worker-01
     - coding  -> spot-worker-03
     - heavy   -> spot-worker-04
     - utility -> spot-worker-02
  2. /stats/routing-audit returns JSON containing expected primary routes
  3. fleet-watch state reports healthy
  4. routing audit file exists and is appended by validation traffic
  5. optional smoke mode quarantine/unquarantine, no restart required

Environment overrides:
  SPOT_BASE_URL, WATCH_STATE_DIR, AUDIT_FILE, FLEET_STATUS_FILE,
  AUDIT_SUMMARY_FILE, SMOKE_WORKER, CURL_TIMEOUT, POLL_INTERVAL, POLL_ATTEMPTS
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --smoke) SMOKE_MODE=1; shift ;;
    --worker) SMOKE_WORKER="$2"; shift 2 ;;
    --base-url) SPOT_BASE_URL="$2"; shift 2 ;;
    --watch-state-dir)
      WATCH_STATE_DIR="$2"
      AUDIT_FILE="${WATCH_STATE_DIR}/routing-audit.jsonl"
      FLEET_STATUS_FILE="${WATCH_STATE_DIR}/fleet-status.json"
      AUDIT_SUMMARY_FILE="${WATCH_STATE_DIR}/routing-audit-summary.json"
      shift 2
      ;;
    --verbose) VERBOSE=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown arg: $1" >&2; usage; exit 2 ;;
  esac
done

if ! command -v jq >/dev/null 2>&1; then
  echo "ERROR: jq is required." >&2
  exit 2
fi
if ! command -v curl >/dev/null 2>&1; then
  echo "ERROR: curl is required." >&2
  exit 2
fi

TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT

PASS_COUNT=0
FAIL_COUNT=0
WARN_COUNT=0

log() { printf '%s\n' "$*"; }
info() { printf '[INFO] %s\n' "$*"; }
pass() { PASS_COUNT=$((PASS_COUNT + 1)); echo "[PASS] $*"; }
fail() { FAIL_COUNT=$((FAIL_COUNT + 1)); echo "[FAIL] $*"; }
warn() {
  WARN_COUNT=$((WARN_COUNT + 1))
  if [[ "$VERBOSE" -eq 1 ]]; then
    echo "[WARN] $*"
  fi
  return 0
}

debug() {
  if [[ "$VERBOSE" -eq 1 ]]; then
    printf '[DBG] %s\n' "$*"
  fi
  return 0
}

ts() { date -u +'%Y-%m-%dT%H:%M:%SZ'; }

http_json() {
  local method="$1"
  local url="$2"
  local body_file="${3:-}"
  local out_file="$4"
  local code_file="$5"

  if [[ -n "$body_file" ]]; then
    curl -sS -X "$method" \
      --connect-timeout 5 \
      --max-time "$CURL_TIMEOUT" \
      -H 'Content-Type: application/json' \
      --data @"$body_file" \
      -o "$out_file" -w '%{http_code}' "$url" > "$code_file"
  else
    curl -sS -X "$method" \
      --connect-timeout 5 \
      --max-time "$CURL_TIMEOUT" \
      -o "$out_file" -w '%{http_code}' "$url" > "$code_file"
  fi
}

wait_for_condition() {
  local description="$1"
  local cmd="$2"
  local attempts="${3:-$POLL_ATTEMPTS}"
  local interval="${4:-$POLL_INTERVAL}"
  local i
  for ((i=1; i<=attempts; i++)); do
    if eval "$cmd"; then
      debug "$description satisfied on attempt $i/$attempts"
      return 0
    fi
    sleep "$interval"
  done
  return 1
}

require_file_json() {
  local file="$1"
  local label="$2"
  if [[ ! -f "$file" ]]; then
    fail "$label missing: $file"
    return 1
  fi
  if jq -e . "$file" >/dev/null 2>&1; then
    pass "$label present and valid JSON"
  else
    fail "$label exists but is not valid JSON: $file"
    return 1
  fi
}

check_role_route() {
  local role="$1"
  local expected_worker="$2"
  local payload="$TMPDIR/exec-${role}.json"
  local response="$TMPDIR/exec-${role}.response.json"
  local code_file="$TMPDIR/exec-${role}.http"
  local token="validator-${role}-$(date +%s)"

  jq -n \
    --arg prompt "Reply with exactly: ${token}" \
    --arg role "$role" \
    '{prompt:$prompt, role:$role, stream:false}' > "$payload"

  if ! http_json POST "${SPOT_BASE_URL}/exec" "$payload" "$response" "$code_file"; then
    fail "${role} route request failed to execute"
    return 1
  fi

  local http_code
  http_code="$(<"$code_file")"
  if [[ ! "$http_code" =~ ^2 ]]; then
    fail "${role} route returned HTTP ${http_code}"
    [[ -s "$response" ]] && warn "${role} route body: $(tr -d '\n' < "$response" | head -c 300)"
    return 1
  fi

  if ! jq -e . "$response" >/dev/null 2>&1; then
    fail "${role} route returned non-JSON body"
    return 1
  fi

  local actual_worker
  actual_worker="$(jq -r '.worker // .selected_worker // .selected // .route.worker // .result.worker // empty' "$response")"
  if [[ -z "$actual_worker" || "$actual_worker" == "null" ]]; then
    fail "${role} route response did not expose worker field"
    return 1
  fi

  if [[ "$actual_worker" == "$expected_worker" ]]; then
    pass "${role} -> ${actual_worker}"
  else
    fail "${role} -> ${actual_worker} (expected ${expected_worker})"
    return 1
  fi
}

run_role_route_checks() {
  local before_lines=0
  [[ -f "$AUDIT_FILE" ]] && before_lines="$(wc -l < "$AUDIT_FILE")"
  debug "routing audit lines before route checks: ${before_lines}"

  check_role_route general spot-worker-01 || true
  check_role_route coding spot-worker-03 || true
  check_role_route heavy spot-worker-04 || true
  check_role_route utility spot-worker-02 || true

  local after_lines=0
  [[ -f "$AUDIT_FILE" ]] && after_lines="$(wc -l < "$AUDIT_FILE")"
  ROUTE_CHECK_BEFORE_LINES="$before_lines"
  ROUTE_CHECK_AFTER_LINES="$after_lines"
  debug "routing audit lines after route checks: ${after_lines}"
}

check_audit_file_append() {
  if [[ ! -f "$AUDIT_FILE" ]]; then
    fail "routing audit file missing after exec validation: $AUDIT_FILE"
    return 1
  fi

  local before_lines="${ROUTE_CHECK_BEFORE_LINES:-0}"
  local after_lines="${ROUTE_CHECK_AFTER_LINES:-0}"

  if (( after_lines > before_lines )); then
    pass "routing audit file appended by validation traffic (${before_lines} -> ${after_lines})"
  else
    fail "routing audit file did not append expected entries (${before_lines} -> ${after_lines})"
    return 1
  fi

  local bad_jsonl=0
  if ! awk 'NF { print }' "$AUDIT_FILE" | tail -n 20 | jq -R 'fromjson? | type == "object"' >/dev/null 2>&1; then
    bad_jsonl=1
  fi
  if [[ "$bad_jsonl" -ne 0 ]]; then
    fail 'recent routing audit entries include invalid JSONL'
    return 1
  fi
}

check_routing_audit_endpoint() {
  local out="$TMPDIR/routing-audit-stats.json"
  local code_file="$TMPDIR/routing-audit-stats.http"

  if ! http_json GET "${SPOT_BASE_URL}/stats/routing-audit" "" "$out" "$code_file"; then
    fail "/stats/routing-audit request failed"
    return 1
  fi

  local http_code
  http_code="$(<"$code_file")"
  if [[ ! "$http_code" =~ ^2 ]]; then
    fail "/stats/routing-audit returned HTTP ${http_code}"
    return 1
  fi

  if ! jq -e . "$out" >/dev/null 2>&1; then
    fail "/stats/routing-audit returned non-JSON body"
    return 1
  fi

  local compact
  compact="$(jq -c . "$out")"
  local missing=0
  for pair in \
    'general:spot-worker-01' \
    'coding:spot-worker-03' \
    'heavy:spot-worker-04' \
    'utility:spot-worker-02'
  do
    local role="${pair%%:*}"
    local worker="${pair##*:}"
    if [[ "$compact" == *"$role"* && "$compact" == *"$worker"* && "$compact" == *"primary"* ]]; then
      debug "/stats/routing-audit contains ${role}/${worker}/primary"
    else
      fail "audit missing ${role} -> ${worker}"
      missing=1
    fi
  done

  [[ "$missing" -eq 0 ]]
}

check_watch_health() {
  require_file_json "$FLEET_STATUS_FILE" "fleet status" || return 1
  require_file_json "$AUDIT_SUMMARY_FILE" "routing audit summary" || return 1

  local fleet_ok=1
  if jq -e '.core_health.ok == true' "$FLEET_STATUS_FILE" >/dev/null 2>&1; then
    pass 'fleet-status core_health.ok is true'
  else
    fail 'fleet-status core_health.ok is not true'
    fleet_ok=0
  fi

  local unhealthy_hosts
  unhealthy_hosts="$(jq -r '
    .hosts
    | to_entries[]
    | select((.value.ssh_ok // true) != true or (.value.service_ok // true) != true)
    | .key
  ' "$FLEET_STATUS_FILE" 2>/dev/null || true)"

  if [[ -z "$unhealthy_hosts" ]]; then
    pass 'fleet-status hosts report ssh_ok/service_ok'
  else
    fail "fleet-status unhealthy hosts: $(echo "$unhealthy_hosts" | paste -sd ', ' -)"
    fleet_ok=0
  fi

  local expected_quarantine_false
  expected_quarantine_false="$(jq -r '
    .hosts
    | to_entries[]
    | select((.value.quarantined // false) == true)
    | .key
  ' "$FLEET_STATUS_FILE" 2>/dev/null || true)"
  if [[ -z "$expected_quarantine_false" ]]; then
    pass 'fleet-status shows no quarantined hosts'
  else
    warn "fleet-status still shows quarantined hosts: $(echo "$expected_quarantine_false" | paste -sd ', ' -)"
  fi

  if [[ "$fleet_ok" -eq 1 ]]; then
  return 0
else
  return 1
fi
}

fetch_fleet_ping() {
  local out="$1"
  local code_file="$2"
  http_json GET "${SPOT_BASE_URL}/fleet/ping" "" "$out" "$code_file"
}

check_worker_runtime_state() {
  local worker="$1"
  local expected_quarantined="$2"
  local expected_eligible="$3"
  local out="$TMPDIR/fleet-ping-${worker}.json"
  local code_file="$TMPDIR/fleet-ping-${worker}.http"

  fetch_fleet_ping "$out" "$code_file" || return 1
  [[ "$(<"$code_file")" =~ ^2 ]] || return 1

  jq -e \
    --arg worker "$worker" \
    --argjson q "$expected_quarantined" \
    --argjson e "$expected_eligible" \
    '.[$worker].quarantined == $q and .[$worker].eligible == $e' \
    "$out" >/dev/null 2>&1
}

check_worker_watch_state() {
  local worker="$1"
  local expected_quarantined="$2"
  jq -e \
    --arg worker "$worker" \
    --argjson q "$expected_quarantined" \
    '.hosts[$worker].quarantined == $q' \
    "$FLEET_STATUS_FILE" >/dev/null 2>&1
}

smoke_quarantine_cycle() {
  local worker="$1"
  local out="$TMPDIR/smoke-quarantine.json"
  local code_file="$TMPDIR/smoke-quarantine.http"

  info "running smoke quarantine cycle for ${worker}"

  if ! http_json POST "${SPOT_BASE_URL}/quarantine/${worker}" "" "$out" "$code_file"; then
    fail "POST /quarantine/${worker} request failed"
    return 1
  fi
  if [[ ! "$(<"$code_file")" =~ ^2 ]]; then
    fail "POST /quarantine/${worker} returned HTTP $(<"$code_file")"
    return 1
  fi
  pass "POST /quarantine/${worker} returned success"

  if wait_for_condition \
    "runtime quarantine state for ${worker}" \
    "check_worker_runtime_state '$worker' true false"; then
    pass "fleet/ping shows ${worker} quarantined=true eligible=false"
  else
    fail "fleet/ping did not reflect quarantine for ${worker}"
    return 1
  fi

  if wait_for_condition \
    "watch quarantine state for ${worker}" \
    "check_worker_watch_state '$worker' true"; then
    pass "fleet-status shows ${worker} quarantined=true"
  else
    warn "fleet-status did not reflect quarantine for ${worker} within polling window"
  fi

  if ! http_json DELETE "${SPOT_BASE_URL}/quarantine/${worker}" "" "$out" "$code_file"; then
    fail "DELETE /quarantine/${worker} request failed"
    return 1
  fi
  if [[ ! "$(<"$code_file")" =~ ^2 ]]; then
    fail "DELETE /quarantine/${worker} returned HTTP $(<"$code_file")"
    return 1
  fi
  pass "DELETE /quarantine/${worker} returned success"

  if wait_for_condition \
    "runtime unquarantine state for ${worker}" \
    "check_worker_runtime_state '$worker' false true"; then
    pass "fleet/ping shows ${worker} quarantined=false eligible=true without restart"
  else
    fail "fleet/ping did not clear quarantine for ${worker}"
    return 1
  fi

  if wait_for_condition \
    "watch unquarantine state for ${worker}" \
    "check_worker_watch_state '$worker' false"; then
    pass "fleet-status shows ${worker} quarantined=false"
  else
    warn "fleet-status did not clear quarantine for ${worker} within polling window"
  fi
}

main() {
  log "=== SPOT FLEET VALIDATION ==="
  log "timestamp: $(ts)"
  log "base_url: ${SPOT_BASE_URL}"
  log "watch_state_dir: ${WATCH_STATE_DIR}"
  log "audit_file: ${AUDIT_FILE}"
  log "smoke_mode: ${SMOKE_MODE}"
  log

  require_file_json "$FLEET_STATUS_FILE" "fleet status" || true
  require_file_json "$AUDIT_SUMMARY_FILE" "routing audit summary" || true
  if [[ -f "$AUDIT_FILE" ]]; then
    pass "routing audit file exists"
  else
    fail "routing audit file missing: $AUDIT_FILE"
  fi

  run_role_route_checks
  check_audit_file_append || true
  check_routing_audit_endpoint || true
  check_watch_health || true

  if [[ "$SMOKE_MODE" -eq 1 ]]; then
    smoke_quarantine_cycle "$SMOKE_WORKER" || true
  else
    info 'smoke mode skipped'
  fi

log
log "=== SUMMARY ==="
log "pass=${PASS_COUNT} warn=${WARN_COUNT} fail=${FAIL_COUNT}"

echo
if [[ "$FAIL_COUNT" -gt 0 ]]; then
  echo "RESULT: FAIL (${FAIL_COUNT} failed, ${PASS_COUNT} passed)"
  exit 1
else
  echo "RESULT: PASS (${PASS_COUNT} checks)"
  exit 0
fi
}

main "$@"

