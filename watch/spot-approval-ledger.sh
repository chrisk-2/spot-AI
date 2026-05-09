#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="${BASE_DIR:-/home/ogre/spot-stack/watch}"
LEDGER_DIR="${LEDGER_DIR:-${BASE_DIR}/contracts/approval-ledger}"
LEDGER_FILE="${LEDGER_FILE:-${LEDGER_DIR}/index.jsonl}"
STATE_FILE="${STATE_FILE:-${LEDGER_DIR}/state.json}"

need() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "ERROR: required command missing: $1" >&2
    exit 2
  }
}

init_ledger() {
  mkdir -p "${LEDGER_DIR}/archive"
  touch "$LEDGER_FILE"

  if [[ ! -f "$STATE_FILE" ]]; then
    cat > "$STATE_FILE" <<'EOF'
{
  "ledger_initialized": true,
  "policy_state": "proposal_only_locked",
  "last_hash": null,
  "records": 0,
  "mutation_performed": false,
  "execution_performed": false
}
EOF
  fi
}

record_hash() {
  jq -c '{
    event_id,
    ts,
    task_id,
    reviewer,
    action,
    approval_status,
    previous_hash
  }' | sha256sum | awk '{print "sha256:" $1}'
}

cmd_append() {
  need jq
  need sha256sum
  init_ledger

  local task_id="${1:-}"
  local reviewer="${2:-}"
  local action="${3:-approved}"
  local approval_status="${4:-approved}"

  [[ -n "$task_id" ]] || { echo "ERROR: task_id required" >&2; exit 2; }
  [[ -n "$reviewer" ]] || { echo "ERROR: reviewer required" >&2; exit 2; }

  local ts event_id previous_hash unsigned record_hash_value

  ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
  event_id="APPROVAL-$(date -u +%Y%m%d-%H%M%S)"
  previous_hash="$(jq -r '.last_hash // null' "$STATE_FILE")"

  unsigned="$(
    jq -c -n \
      --arg event_id "$event_id" \
      --arg ts "$ts" \
      --arg task_id "$task_id" \
      --arg reviewer "$reviewer" \
      --arg action "$action" \
      --arg approval_status "$approval_status" \
      --argjson previous_hash "$(jq -n --arg h "$previous_hash" 'if $h == "null" then null else $h end')" \
      '{
        event_id: $event_id,
        ts: $ts,
        task_id: $task_id,
        reviewer: $reviewer,
        action: $action,
        approval_status: $approval_status,
        previous_hash: $previous_hash,
        policy_state: "proposal_only_locked",
        mutation_performed: false,
        execution_performed: false
      }'
  )"

  record_hash_value="$(echo "$unsigned" | record_hash)"

  echo "$unsigned" | jq -c --arg record_hash "$record_hash_value" '. + {record_hash: $record_hash}' >> "$LEDGER_FILE"

  jq \
    --arg last_hash "$record_hash_value" \
    '.last_hash = $last_hash | .records = (.records + 1)' \
    "$STATE_FILE" > "${STATE_FILE}.tmp"

  mv "${STATE_FILE}.tmp" "$STATE_FILE"

  tail -n 1 "$LEDGER_FILE" | jq .
}

cmd_verify() {
  need jq
  need sha256sum
  init_ledger

  local previous_hash="null"
  local failures=0
  local line_no=0
  local expected actual

  while IFS= read -r line || [[ -n "$line" ]]; do
    [[ -n "$line" ]] || continue
    line_no=$((line_no + 1))

    if ! echo "$line" | jq -e . >/dev/null; then
      echo "FAIL: line ${line_no}: invalid JSON"
      failures=$((failures + 1))
      continue
    fi

    if [[ "$(echo "$line" | jq -r '.policy_state')" != "proposal_only_locked" ]]; then
      echo "FAIL: line ${line_no}: invalid policy_state"
      failures=$((failures + 1))
    fi

    if [[ "$(echo "$line" | jq -r '.mutation_performed')" != "false" ]]; then
      echo "FAIL: line ${line_no}: mutation_performed not false"
      failures=$((failures + 1))
    fi

    if [[ "$(echo "$line" | jq -r '.execution_performed')" != "false" ]]; then
      echo "FAIL: line ${line_no}: execution_performed not false"
      failures=$((failures + 1))
    fi

    actual="$(echo "$line" | jq -r '.record_hash')"

    expected="$(
      echo "$line" |
        jq -c '{
          event_id,
          ts,
          task_id,
          reviewer,
          action,
          approval_status,
          previous_hash
        }' |
        sha256sum |
        awk '{print "sha256:" $1}'
    )"

    if [[ "$actual" != "$expected" ]]; then
      echo "FAIL: line ${line_no}: record_hash mismatch"
      failures=$((failures + 1))
    fi

    if [[ "$(echo "$line" | jq -r '.previous_hash // "null"')" != "$previous_hash" ]]; then
      echo "FAIL: line ${line_no}: previous_hash chain mismatch"
      failures=$((failures + 1))
    fi

    previous_hash="$actual"
  done < "$LEDGER_FILE"

  if [[ "$failures" -ne 0 ]]; then
    echo "RESULT: FAIL failures=${failures}" >&2
    exit 1
  fi

  jq -n \
    --arg file "$LEDGER_FILE" \
    --argjson records "$line_no" \
    --arg last_hash "$previous_hash" \
    '{
      ok: true,
      verified: true,
      ledger_file: $file,
      records_checked: $records,
      last_hash: (if $last_hash == "null" then null else $last_hash end),
      policy_state: "proposal_only_locked",
      mutation_performed: false,
      execution_performed: false
    }'
}

cmd_summary() {
  need jq
  init_ledger

  jq -s '{
    ok: true,
    records: length,
    by_action: (group_by(.action) | map({action: .[0].action, count: length})),
    mutation_performed: any(.mutation_performed == true),
    execution_performed: any(.execution_performed == true),
    policy_state: "proposal_only_locked"
  }' "$LEDGER_FILE"
}

case "${1:-}" in
  append) shift; cmd_append "$@" ;;
  verify) cmd_verify ;;
  summary) cmd_summary ;;
  show) jq . "$LEDGER_FILE" ;;
  *)
    echo "Usage:"
    echo "  spot-approval-ledger.sh append <task_id> <reviewer> [action] [approval_status]"
    echo "  spot-approval-ledger.sh verify"
    echo "  spot-approval-ledger.sh summary"
    echo "  spot-approval-ledger.sh show"
    exit 2
    ;;
esac
