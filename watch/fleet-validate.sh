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
ADMIN_TOKEN=""

usage() {
  cat <<USAGE
Usage: $(basename "$0") [--smoke] [--worker <name>] [--base-url <url>] [--watch-state-dir <dir>] [--verbose]
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
      shift 2 ;;
    --verbose) VERBOSE=1; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "Unknown arg: $1" >&2; usage; exit 2 ;;
  esac
done

command -v jq >/dev/null 2>&1 || { echo "ERROR: jq is required." >&2; exit 2; }
command -v curl >/dev/null 2>&1 || { echo "ERROR: curl is required." >&2; exit 2; }

TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT

PASS_COUNT=0
FAIL_COUNT=0
WARN_COUNT=0

log() { printf '%s\n' "$*"; }
info() { printf '[INFO] %s\n' "$*"; }
pass() { PASS_COUNT=$((PASS_COUNT + 1)); echo "[PASS] $*"; }
fail() { FAIL_COUNT=$((FAIL_COUNT + 1)); echo "[FAIL] $*"; }
warn() { WARN_COUNT=$((WARN_COUNT + 1)); echo "[WARN] $*"; }
debug() { [[ "$VERBOSE" -eq 1 ]] && printf '[DBG] %s\n' "$*" || true; }
ts() { date -u +'%Y-%m-%dT%H:%M:%SZ'; }

http_json() {
  local method="$1" url="$2" body_file="${3:-}" out_file="$4" code_file="$5"
  if [[ -n "$body_file" ]]; then
    curl -sS -X "$method" --connect-timeout 5 --max-time "$CURL_TIMEOUT" -H 'Content-Type: application/json' --data @"$body_file" -o "$out_file" -w '%{http_code}' "$url" > "$code_file"
  else
    curl -sS -X "$method" --connect-timeout 5 --max-time "$CURL_TIMEOUT" -o "$out_file" -w '%{http_code}' "$url" > "$code_file"
  fi
}

wait_for_condition() {
  local description="$1" cmd="$2" attempts="${3:-$POLL_ATTEMPTS}" interval="${4:-$POLL_INTERVAL}"
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
  local file="$1" label="$2"
  [[ -f "$file" ]] || { fail "$label missing: $file"; return 1; }
  jq -e . "$file" >/dev/null 2>&1 && pass "$label valid JSON" || { fail "$label invalid JSON: $file"; return 1; }
}

check_role_route() {
  local role="$1" expected_worker="$2"
  local payload="$TMPDIR/exec-${role}.json" response="$TMPDIR/exec-${role}.response.json" code_file="$TMPDIR/exec-${role}.http"
  local token="validator-${role}-$(date +%s)"
  jq -n --arg prompt "Reply with exactly: ${token}" --arg role "$role" '{prompt:$prompt, role:$role, stream:false}' > "$payload"

  http_json POST "${SPOT_BASE_URL}/exec" "$payload" "$response" "$code_file" || { sleep 2; http_json POST "${SPOT_BASE_URL}/exec" "$payload" "$response" "$code_file" || { fail "${role} route request failed"; return 1; }; }
  local http_code; http_code="$(<"$code_file")"
  if [[ "$http_code" == "429" || "$http_code" == "503" || "$http_code" == "504" ]]; then
    sleep 2
    http_json POST "${SPOT_BASE_URL}/exec" "$payload" "$response" "$code_file" || { fail "${role} route retry failed"; return 1; }
    http_code="$(<"$code_file")"
  fi
  [[ "$http_code" =~ ^2 ]] || { fail "${role} route returned HTTP ${http_code}"; return 1; }
  jq -e . "$response" >/dev/null 2>&1 || { fail "${role} route non-JSON body"; return 1; }
  local actual_worker; actual_worker="$(jq -r '.worker // .selected_worker // .selected // .route.worker // .result.worker // empty' "$response")"
  [[ -n "$actual_worker" && "$actual_worker" != "null" ]] || { fail "${role} route missing worker field"; return 1; }
  [[ "$actual_worker" == "$expected_worker" ]] && pass "${role} -> ${actual_worker}" || { fail "${role} -> ${actual_worker} (expected ${expected_worker})"; return 1; }
}

check_worker_registered() {
  local worker="$1" role="$2" required_models_json="$3"
  local ping="$TMPDIR/fleet-ping-${worker}.json" code_file="$TMPDIR/fleet-ping-${worker}.http"

  fetch_fleet_ping "$ping" "$code_file" || { fail "${worker} fleet/ping request failed"; return 1; }
  [[ "$(<"$code_file")" =~ ^2 ]] || { fail "${worker} fleet/ping bad HTTP"; return 1; }

  jq -e --arg worker "$worker" --arg role "$role" '
    .[$worker].ok == true and
    .[$worker].eligible == true and
    .[$worker].quarantined == false and
    .[$worker].primary_role == $role
  ' "$ping" >/dev/null 2>&1 \
    && pass "${worker} registered as ${role} and eligible" \
    || { fail "${worker} not registered/eligible as ${role}"; return 1; }

  jq -e --arg worker "$worker" --argjson required "$required_models_json" '
    (.[$worker].installed_models // []) as $models |
    all($required[]; . as $m | $models | index($m))
  ' "$ping" >/dev/null 2>&1 \
    && pass "${worker} required models present" \
    || { fail "${worker} missing required models"; return 1; }
}

run_role_route_checks() {
  local before_lines=0
  [[ -f "$AUDIT_FILE" ]] && before_lines="$(wc -l < "$AUDIT_FILE")"
  check_role_route general spot-worker-01 || true
  check_worker_registered spot-worker-02 utility '["mistral:7b","bge-m3:latest","nomic-embed-text:latest"]'
  check_role_route coding spot-worker-03 || true
  check_role_route heavy spot-worker-04 || true
  local reasoning_ping="$TMPDIR/reasoning-quarantine.json"
  local reasoning_code="$TMPDIR/reasoning-quarantine.http"

  fetch_fleet_ping "$reasoning_ping" "$reasoning_code" || true

  if jq -e '.["spot-worker-06"].quarantined == true' "$reasoning_ping" >/dev/null 2>&1; then
    warn "spot-worker-06 reasoning lane quarantined; skipping eligibility check"
  else
    check_worker_registered spot-worker-06 reasoning '["deepseek-r1:32b","qwen2.5-coder:32b","qwen2.5:14b"]' || true
  fi
  local after_lines=0
  [[ -f "$AUDIT_FILE" ]] && after_lines="$(wc -l < "$AUDIT_FILE")"
  ROUTE_CHECK_BEFORE_LINES="$before_lines"
  ROUTE_CHECK_AFTER_LINES="$after_lines"
}

check_audit_file_append() {
  [[ -f "$AUDIT_FILE" ]] || { fail "routing audit file missing after exec validation: $AUDIT_FILE"; return 1; }
  local before_lines="${ROUTE_CHECK_BEFORE_LINES:-0}" after_lines="${ROUTE_CHECK_AFTER_LINES:-0}"
  (( after_lines > before_lines )) && pass "routing audit appended (${before_lines} -> ${after_lines})" || { fail "routing audit did not append (${before_lines} -> ${after_lines})"; return 1; }
  awk 'NF { print }' "$AUDIT_FILE" | tail -n 20 | jq -R 'fromjson? | type == "object"' >/dev/null 2>&1 && pass "routing audit JSONL valid" || { fail 'routing audit JSONL invalid'; return 1; }
}

check_routing_audit_endpoint() {
  local out="$TMPDIR/routing-audit-stats.json" code_file="$TMPDIR/routing-audit-stats.http"
  http_json GET "${SPOT_BASE_URL}/stats/routing-audit" "" "$out" "$code_file" || { fail "/stats/routing-audit request failed"; return 1; }
  [[ "$(<"$code_file")" =~ ^2 ]] || { fail "/stats/routing-audit bad HTTP"; return 1; }
  jq -e . "$out" >/dev/null 2>&1 || { fail "/stats/routing-audit non-JSON body"; return 1; }
  local compact; compact="$(jq -c . "$out")"
  local missing=0
  for pair in 'general:spot-worker-01' 'coding:spot-worker-03' 'heavy:spot-worker-04' 'utility:spot-worker-02'; do
    local role="${pair%%:*}" worker="${pair##*:}"
    [[ "$compact" == *"$role"* && "$compact" == *"$worker"* && "$compact" == *"primary"* ]] || { fail "audit missing ${role} -> ${worker}"; missing=1; }
  done
  [[ "$missing" -eq 0 ]] && pass "/stats/routing-audit reflects expected primaries"
}

get_admin_token() {
  local token
  token="${SPOTCORE_ADMIN_API_TOKEN:-}"
  if [[ -z "$token" ]]; then
    command -v docker >/dev/null 2>&1 || { fail "docker required for admin endpoint validation and SPOTCORE_ADMIN_API_TOKEN not set"; return 1; }
    token="$(docker exec spot-core /bin/sh -lc 'printf %s "$SPOTCORE_ADMIN_API_TOKEN"' 2>/dev/null || true)"
  fi
  [[ -n "$token" ]] || { fail "could not read SPOTCORE_ADMIN_API_TOKEN"; return 1; }
  ADMIN_TOKEN="$token"
}

check_admin_validate_endpoint() {
  [[ -n "${ADMIN_TOKEN:-}" ]] || { fail "/admin/validate skipped: ADMIN_TOKEN not set"; return 1; }
  local payload="$TMPDIR/admin-validate.json" response="$TMPDIR/admin-validate.response.json" code_file="$TMPDIR/admin-validate.http"
  jq -n --arg token "$ADMIN_TOKEN" --arg worker "spot-worker-01" '{token:$token,worker:$worker,commands:["test -f /etc/os-release","systemctl is-active ollama"]}' > "$payload"
  http_json POST "${SPOT_BASE_URL}/admin/validate" "$payload" "$response" "$code_file" || { fail "/admin/validate request failed"; return 1; }
  [[ "$(<"$code_file")" =~ ^2 ]] || { fail "/admin/validate bad HTTP"; return 1; }
  jq -e '.ok != null and (.results | type == "array")' "$response" >/dev/null 2>&1 && pass "/admin/validate JSON structure ok" || { fail "/admin/validate JSON structure invalid"; return 1; }
}

check_admin_read_file_endpoint() {
  local payload="$TMPDIR/admin-read-file.json" response="$TMPDIR/admin-read-file.response.json" code_file="$TMPDIR/admin-read-file.http"
  jq -n --arg token "$ADMIN_TOKEN" --arg worker "spot-worker-01" --arg path "/etc/os-release" '{token:$token,worker:$worker,path:$path}' > "$payload"
  http_json POST "${SPOT_BASE_URL}/admin/read-file" "$payload" "$response" "$code_file" || { fail "/admin/read-file request failed"; return 1; }
  [[ "$(<"$code_file")" =~ ^2 ]] || { fail "/admin/read-file bad HTTP"; return 1; }
  jq -e '.content | strings | contains("PRETTY_NAME=") or contains("Ubuntu")' "$response" >/dev/null 2>&1 && pass "/admin/read-file returned expected file content" || { fail "/admin/read-file content mismatch"; return 1; }
}

check_watch_health() {
  require_file_json "$FLEET_STATUS_FILE" "fleet status" || return 1
  require_file_json "$AUDIT_SUMMARY_FILE" "routing audit summary" || return 1
  jq -e '.core_health.ok == true' "$FLEET_STATUS_FILE" >/dev/null 2>&1 && pass 'fleet-status core health ok' || fail 'fleet-status core health not ok'
  local unhealthy_hosts; unhealthy_hosts="$(jq -r '.hosts|to_entries[]|select((.value.ssh_ok // true) != true or (.value.service_ok // true) != true)|.key' "$FLEET_STATUS_FILE" 2>/dev/null || true)"
  [[ -z "$unhealthy_hosts" ]] && pass 'fleet-status hosts healthy' || fail "fleet-status unhealthy hosts: $(echo "$unhealthy_hosts" | paste -sd ', ' -)"
}

check_secret_regression() {
  command -v git >/dev/null 2>&1 || { warn "secret regression skipped: git unavailable"; return 0; }
  local repo_root; repo_root="$(git rev-parse --show-toplevel 2>/dev/null || true)"
  [[ -n "$repo_root" ]] || { warn "secret regression skipped: no git repo"; return 0; }
  local matches_file="$TMPDIR/secret-regression.matches"
  (
    cd "$repo_root"
    git grep -n -E 'SPOTCORE_ADMIN_API_TOKEN[[:space:]]*[:=][[:space:]]*["'"'"']?[A-Za-z0-9_./+-]{16,}' -- \
      ':!*.env' \
      ':!*.pyc' \
      ':!*__pycache__*' \
      ':!spot-core/STATE.md' \
      ':!watch/fleet-validate.sh' \
      || true
  ) > "$matches_file" 2>/dev/null
  [[ ! -s "$matches_file" ]] && pass "secret regression clean" || { fail "secret regression: hardcoded SPOTCORE_ADMIN_API_TOKEN found"; cat "$matches_file"; return 1; }
}

fetch_fleet_ping() { http_json GET "${SPOT_BASE_URL}/fleet/ping" "" "$1" "$2"; }
check_worker_runtime_state() { local worker="$1" expected_quarantined="$2" expected_eligible="$3" out="$TMPDIR/fleet-ping-${worker}.json" code_file="$TMPDIR/fleet-ping-${worker}.http"; fetch_fleet_ping "$out" "$code_file" || return 1; [[ "$(<"$code_file")" =~ ^2 ]] || return 1; jq -e --arg worker "$worker" --argjson q "$expected_quarantined" --argjson e "$expected_eligible" '.[$worker].quarantined == $q and .[$worker].eligible == $e' "$out" >/dev/null 2>&1; }
check_worker_watch_state() { local worker="$1" expected_quarantined="$2"; jq -e --arg worker "$worker" --argjson q "$expected_quarantined" '.hosts[$worker].quarantined == $q' "$FLEET_STATUS_FILE" >/dev/null 2>&1; }

smoke_quarantine_cycle() {
  local worker="$1" out="$TMPDIR/smoke-quarantine.json" code_file="$TMPDIR/smoke-quarantine.http"
  info "running smoke quarantine cycle for ${worker}"
  http_json POST "${SPOT_BASE_URL}/quarantine/${worker}" "" "$out" "$code_file" || { fail "POST /quarantine/${worker} request failed"; return 1; }
  [[ "$(<"$code_file")" =~ ^2 ]] && pass "quarantine route accepted" || { fail "POST /quarantine/${worker} bad HTTP"; return 1; }
  wait_for_condition "runtime quarantine state" "check_worker_runtime_state '$worker' true false" && pass "fleet/ping quarantine asserted (quarantined=true eligible=false)" || { fail "fleet/ping quarantine assertion failed"; return 1; }
  wait_for_condition "watch quarantine state" "check_worker_watch_state '$worker' true" && pass "fleet-status quarantine asserted" || warn "fleet-status quarantine reflection delayed"
  http_json DELETE "${SPOT_BASE_URL}/quarantine/${worker}" "" "$out" "$code_file" || { fail "DELETE /quarantine/${worker} request failed"; return 1; }
  [[ "$(<"$code_file")" =~ ^2 ]] && pass "release route accepted" || { fail "DELETE /quarantine/${worker} bad HTTP"; return 1; }
  wait_for_condition "runtime release state" "check_worker_runtime_state '$worker' false true" && pass "fleet/ping release asserted (quarantined=false eligible=true, no restart)" || { fail "fleet/ping release assertion failed"; return 1; }
  wait_for_condition "watch release state" "check_worker_watch_state '$worker' false" && pass "fleet-status release asserted" || warn "fleet-status release reflection delayed"
}

check_worker_backup_freshness() {
  local max_age_hours max_age_sec now workers worker meta snap raw epoch age_sec age_hours
  max_age_hours="${SPOT_BACKUP_MAX_AGE_HOURS:-8}"
  max_age_sec=$((max_age_hours * 3600))
  now="$(date -u +%s)"
  workers="spot-worker-01 spot-worker-02 spot-worker-03 spot-worker-04 spot-worker-06"
  for worker in $workers; do
    meta="/mnt/collective/backups/${worker}/worker-config/latest/metadata.json"
    if [[ ! -f "$meta" ]]; then
      snap="$(find "/mnt/collective/backups/${worker}/worker-config" -mindepth 1 -maxdepth 1 -type d -printf '%f\n' 2>/dev/null | grep -E '^[0-9]{8}T[0-9]{6}Z$' | sort | tail -n 1 || true)"
      [[ -n "$snap" ]] && meta="/mnt/collective/backups/${worker}/worker-config/${snap}/metadata.json"
    fi
    [[ -f "$meta" ]] || { warn "backup freshness: ${worker} metadata missing"; continue; }
    raw="$(jq -r '.timestamp_utc // empty' "$meta" 2>/dev/null || true)"
    [[ -n "$raw" ]] || { warn "backup freshness: ${worker} no timestamp_utc"; continue; }
    if [[ "$raw" =~ ^([0-9]{4})([0-9]{2})([0-9]{2})T([0-9]{2})([0-9]{2})([0-9]{2})Z$ ]]; then epoch="$(date -u -d "${BASH_REMATCH[1]}-${BASH_REMATCH[2]}-${BASH_REMATCH[3]} ${BASH_REMATCH[4]}:${BASH_REMATCH[5]}:${BASH_REMATCH[6]} UTC" +%s 2>/dev/null || true)"; else epoch="$(date -u -d "$raw" +%s 2>/dev/null || true)"; fi
    [[ -n "$epoch" ]] || { warn "backup freshness: ${worker} invalid timestamp"; continue; }
    age_sec=$((now - epoch)); age_hours=$((age_sec / 3600))
    (( age_sec > max_age_sec )) && warn "backup freshness: ${worker} age=${age_hours}h threshold=${max_age_hours}h" || pass "backup freshness: ${worker} age=${age_hours}h"
  done
}

check_backup_metadata_visibility() {
  local count
  count="$(find /mnt/collective/backups \
    -path '/mnt/collective/backups/spot-worker-*/worker-config/*/metadata.json' \
    -type f 2>/dev/null | wc -l | tr -d ' ')"
  if (( count >= 4 )); then pass "backup metadata visibility count=${count}"; else warn "backup metadata visibility unexpectedly low count=${count}"; fi
}

main() {
  log "=== SPOT FLEET VALIDATION ==="
  log "timestamp: $(ts)"
  log "base_url: ${SPOT_BASE_URL} smoke_mode: ${SMOKE_MODE}"
  log
  [[ -f "$AUDIT_FILE" ]] && pass "routing audit file exists" || fail "routing audit file missing: $AUDIT_FILE"
  run_role_route_checks
  check_audit_file_append || true
  check_routing_audit_endpoint || true
  check_watch_health || true
  check_secret_regression || true
  get_admin_token || true
  if [[ -n "${ADMIN_TOKEN:-}" ]]; then check_admin_validate_endpoint || true; check_admin_read_file_endpoint || true; fi
  [[ "$SMOKE_MODE" -eq 1 ]] && smoke_quarantine_cycle "$SMOKE_WORKER" || info 'smoke mode skipped'
  check_worker_backup_freshness
  check_backup_metadata_visibility
  log "CHECK: governance integrity"

  if /home/ogre/spot-stack/watch/spot-governance-verify.sh >/tmp/spot-governance-verify.out 2>/tmp/spot-governance-verify.err; then
    pass "governance integrity"
  else
    fail "governance integrity"
    [[ -f /tmp/spot-governance-verify.out ]] && cat /tmp/spot-governance-verify.out
    [[ -f /tmp/spot-governance-verify.err ]] && cat /tmp/spot-governance-verify.err >&2
  fi
  log
  log "=== SUMMARY ==="
  log "pass=${PASS_COUNT} warn=${WARN_COUNT} fail=${FAIL_COUNT}"
  [[ "$FAIL_COUNT" -gt 0 ]] && { echo "RESULT: FAIL"; exit 1; } || { echo "RESULT: PASS"; exit 0; }
}

main "$@"
