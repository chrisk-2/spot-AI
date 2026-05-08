#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="${BASE_DIR:-/home/ogre/spot-stack/watch}"
JOURNAL_DIR="${JOURNAL_DIR:-${BASE_DIR}/contracts/executor-journal}"
JOURNAL_FILE="${JOURNAL_FILE:-${JOURNAL_DIR}/index.jsonl}"
CONTRACT_VERIFIER="${CONTRACT_VERIFIER:-${BASE_DIR}/spot-executor-contract.sh}"

usage() {
  cat <<USAGE
Usage:
  spot-executor-journal.sh append <event_type> <contract.json>
  spot-executor-journal.sh list [count]
  spot-executor-journal.sh verify
  spot-executor-journal.sh summary
USAGE
}

need() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "ERROR: required command missing: $1" >&2
    exit 2
  }
}

init_journal() {
  mkdir -p "$JOURNAL_DIR"
  touch "$JOURNAL_FILE"
}

cmd_append() {
  need jq
  need sha256sum

  local event_type="${1:-}"
  local contract_file="${2:-}"

  [[ -n "$event_type" ]] || { echo "ERROR: event_type required" >&2; exit 2; }
  [[ -n "$contract_file" ]] || { echo "ERROR: contract file required" >&2; exit 2; }
  [[ -f "$contract_file" ]] || { echo "ERROR: contract not found: $contract_file" >&2; exit 2; }
  [[ -x "$CONTRACT_VERIFIER" ]] || { echo "ERROR: verifier not executable: $CONTRACT_VERIFIER" >&2; exit 2; }

  case "$event_type" in
    contract_verified|task_proposed|task_reviewed|task_approved|task_approval_revoked|task_rejected|task_completed|task_failed) ;;
    *)
      echo "ERROR: event_type not allowed: $event_type" >&2
      exit 2
      ;;
  esac

  init_journal

  local verified checksum ts
  verified="$($CONTRACT_VERIFIER verify "$contract_file")"
  checksum="$(sha256sum "$contract_file" | awk '{print $1}')"
  ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

  jq -c -n \
    --arg ts "$ts" \
    --arg event_type "$event_type" \
    --arg contract_file "$contract_file" \
    --arg contract_sha256 "$checksum" \
    --argjson verification "$verified" \
    '{
      ts: $ts,
      event_type: $event_type,
      contract_file: $contract_file,
      contract_sha256: $contract_sha256,
      verification: $verification,
      append_only: true,
      journal_version: 1,
      journal_mode: "append_only_audit",
      mutation_performed: false,
      execution_performed: false,
      service_restart_performed: false,
      network_mutation_performed: false,
      live_write_performed: false,
      spot_core_apply_required: true
    }' >> "$JOURNAL_FILE"

  tail -n 1 "$JOURNAL_FILE" | jq .
}

cmd_list() {
  need jq
  [[ -f "$JOURNAL_FILE" ]] || {
    echo "ERROR: journal file missing: $JOURNAL_FILE" >&2
    exit 2
  }

  [[ -s "$JOURNAL_FILE" ]] || {
    echo "ERROR: journal file empty" >&2
    exit 2
  }
  init_journal

  local count="${1:-20}"
  tail -n "$count" "$JOURNAL_FILE" | jq .
}

cmd_verify() {
  need jq
  init_journal

  local failures=0
  local line_no=0

  while IFS= read -r line || [[ -n "$line" ]]; do
    line_no=$((line_no + 1))
    [[ -n "$line" ]] || continue

    if ! echo "$line" | jq -e . >/dev/null; then
      echo "FAIL: line ${line_no}: invalid JSON"
      failures=$((failures + 1))
      continue
    fi

    if [[ "$(echo "$line" | jq -r '.append_only')" != "true" ]]; then
      echo "FAIL: line ${line_no}: append_only not true"
      failures=$((failures + 1))
    fi

    if [[ "$(echo "$line" | jq -r '.journal_version')" != "1" ]]; then
      echo "FAIL: line ${line_no}: invalid journal_version"
      failures=$((failures + 1))
    fi

    if [[ "$(echo "$line" | jq -r '.journal_mode')" != "append_only_audit" ]]; then
      echo "FAIL: line ${line_no}: invalid journal_mode"
      failures=$((failures + 1))
    fi

    for field in mutation_performed execution_performed service_restart_performed network_mutation_performed live_write_performed; do
      if [[ "$(echo "$line" | jq -r ".${field}")" != "false" ]]; then
        echo "FAIL: line ${line_no}: ${field} not false"
        failures=$((failures + 1))
      fi
    done
  done < "$JOURNAL_FILE"

  if [[ "$failures" -eq 0 ]]; then
    jq -n --arg file "$JOURNAL_FILE" --argjson lines "$line_no" '{
      ok: true,
      verified: true,
      journal_file: $file,
      lines_checked: $lines,
      mutation_performed: false,
      execution_performed: false
    }'
    exit 0
  fi

  echo "RESULT: FAIL failures=${failures}" >&2
  exit 1
}

cmd_summary() {
  need jq
  init_journal

  jq -s '{
    ok: true,
    journal_file: "'"$JOURNAL_FILE"'",
    entries: length,
    by_event_type: (group_by(.event_type) | map({event_type: .[0].event_type, count: length})),
    mutation_performed: any(.mutation_performed == true),
    execution_performed: any(.execution_performed == true),
    service_restart_performed: any(.service_restart_performed == true),
    network_mutation_performed: any(.network_mutation_performed == true),
    live_write_performed: any(.live_write_performed == true)
  }' "$JOURNAL_FILE"
}

case "${1:-}" in
  append) shift; cmd_append "$@" ;;
  list) shift; cmd_list "$@" ;;
  verify) cmd_verify ;;
  summary) cmd_summary ;;
  -h|--help|help|"") usage ;;
  *) echo "ERROR: unknown command: ${1:-}" >&2; usage >&2; exit 2 ;;
esac
