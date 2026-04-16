#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8787}"
TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT

pass() { echo "[PASS] $*"; }
fail() { echo "[FAIL] $*" >&2; exit 1; }
info() { echo; echo "== $* =="; }

post_json() {
  local method="$1"
  local url="$2"
  local data="${3:-}"
  if [[ -n "$data" ]]; then
    curl -sS -X "$method" "$url" \
      -H 'Content-Type: application/json' \
      -d "$data"
  else
    curl -sS -X "$method" "$url"
  fi
}

exec_role() {
  local role="$1"
  local prompt="$2"
  local outfile="$3"
  local model="${4:-}"

  if [[ -n "$model" ]]; then
    post_json POST "$BASE_URL/exec" "{
      \"prompt\": \"$prompt\",
      \"role\": \"$role\",
      \"model\": \"$model\",
      \"stream\": false
    }" > "$outfile"
  else
    post_json POST "$BASE_URL/exec" "{
      \"prompt\": \"$prompt\",
      \"role\": \"$role\",
      \"stream\": false
    }" > "$outfile"
  fi
}

assert_worker() {
  local file="$1"
  local expected_worker="$2"
  local role="$3"

  local ok worker
  ok="$(jq -r '.ok // false' "$file")"
  worker="$(jq -r '.worker // empty' "$file")"

  [[ "$ok" == "true" ]] || fail "$role did not return ok=true: $(cat "$file")"
  [[ "$worker" == "$expected_worker" ]] || fail "$role routed to $worker, expected $expected_worker: $(cat "$file")"
  pass "$role routed to $expected_worker"
}

assert_failure_contains() {
  local file="$1"
  local needle="$2"
  local role="$3"

  jq -e '.detail.message' "$file" >/dev/null 2>&1 || fail "$role did not fail as expected: $(cat "$file")"
  grep -q "$needle" "$file" || fail "$role failure did not contain '$needle': $(cat "$file")"
  pass "$role failed cleanly as expected"
}

quarantine_worker() {
  local worker="$1"
  local reason="$2"
  post_json POST "$BASE_URL/quarantine/$worker?seconds=120&reason=$reason" | jq .
}

unquarantine_worker() {
  local worker="$1"
  post_json DELETE "$BASE_URL/quarantine/$worker" | jq .
}

show_recent() {
  curl -sS "$BASE_URL/stats/recent-decisions?limit=20" | jq
}

info "Baseline routing checks"

exec_role general "Reply with exactly: general-baseline" "$TMPDIR/general.json"
jq '{ok,worker,gpu_lane,model,response}' "$TMPDIR/general.json"
assert_worker "$TMPDIR/general.json" "spot-worker-01" "general baseline"

exec_role coding "Write exactly: coding-baseline" "$TMPDIR/coding.json"
jq '{ok,worker,gpu_lane,model,response}' "$TMPDIR/coding.json"
assert_worker "$TMPDIR/coding.json" "spot-worker-03" "coding baseline"

exec_role heavy "Reply with exactly: heavy-baseline" "$TMPDIR/heavy.json"
jq '{ok,worker,gpu_lane,model,response}' "$TMPDIR/heavy.json"
assert_worker "$TMPDIR/heavy.json" "spot-worker-04" "heavy baseline"

exec_role utility "Reply with exactly: utility-baseline" "$TMPDIR/utility.json" "phi3.5:latest"
jq '{ok,worker,gpu_lane,model,response}' "$TMPDIR/utility.json"
assert_worker "$TMPDIR/utility.json" "spot-worker-02" "utility baseline"

info "Coding fallback test: quarantine spot-worker-03 -> expect spot-worker-01"
quarantine_worker "spot-worker-03" "test_coding_fallback" >/dev/null
exec_role coding "Write exactly: coding-fallback" "$TMPDIR/coding_fallback.json"
jq '{ok,worker,gpu_lane,model,response}' "$TMPDIR/coding_fallback.json"
assert_worker "$TMPDIR/coding_fallback.json" "spot-worker-01" "coding fallback"
unquarantine_worker "spot-worker-03" >/dev/null

info "Heavy fallback test: quarantine spot-worker-04 -> expect spot-worker-01"
quarantine_worker "spot-worker-04" "test_heavy_fallback" >/dev/null
exec_role heavy "Reply with exactly: heavy-fallback" "$TMPDIR/heavy_fallback.json"
jq '{ok,worker,gpu_lane,model,response}' "$TMPDIR/heavy_fallback.json"
assert_worker "$TMPDIR/heavy_fallback.json" "spot-worker-01" "heavy fallback"
unquarantine_worker "spot-worker-04" >/dev/null

info "General no-fallback test: quarantine spot-worker-01 -> expect failure"
quarantine_worker "spot-worker-01" "test_general_no_fallback" >/dev/null
exec_role general "Reply with exactly: general-should-fail" "$TMPDIR/general_fail.json" || true
jq . "$TMPDIR/general_fail.json"
assert_failure_contains "$TMPDIR/general_fail.json" "no healthy eligible workers" "general no-fallback"
unquarantine_worker "spot-worker-01" >/dev/null

info "Utility no-fallback test: quarantine spot-worker-02 -> expect failure"
quarantine_worker "spot-worker-02" "test_utility_no_fallback" >/dev/null
exec_role utility "Reply with exactly: utility-should-fail" "$TMPDIR/utility_fail.json" "phi3.5:latest" || true
jq . "$TMPDIR/utility_fail.json"
assert_failure_contains "$TMPDIR/utility_fail.json" "no healthy eligible workers" "utility no-fallback"
unquarantine_worker "spot-worker-02" >/dev/null

info "Recent decisions"
show_recent

info "All fallback validation checks passed"
