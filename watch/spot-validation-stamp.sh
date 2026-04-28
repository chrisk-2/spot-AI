#!/usr/bin/env bash
set -Eeuo pipefail

REPO="${REPO:-/home/ogre/spot-stack}"
STATE_DIR="${STATE_DIR:-${REPO}/watch/state}"
STAMP_FILE="${STAMP_FILE:-${STATE_DIR}/operator-validation.json}"
LOG_DIR="${LOG_DIR:-${REPO}/watch/logs}"
LOG_FILE="${LOG_FILE:-${LOG_DIR}/operator-validation.log}"
TAIL_LINES="${TAIL_LINES:-40}"

usage(){
  cat <<USAGE
Usage:
  $(basename "$0") -- <command> [args...]

Examples:
  $(basename "$0") -- spot validate
  $(basename "$0") -- spot validate-smoke
USAGE
}

main(){
  if [[ "${1:-}" != "--" ]]; then
    usage >&2
    exit 2
  fi
  shift
  if [[ "$#" -lt 1 ]]; then
    usage >&2
    exit 2
  fi

  mkdir -p "$STATE_DIR" "$LOG_DIR"

  cd "$REPO"

  local started_at finished_at start_epoch finish_epoch duration exit_code status tmp_log
  started_at="$(date -u +'%Y-%m-%dT%H:%M:%SZ')"
  start_epoch="$(date -u +%s)"
  tmp_log="$(mktemp)"

  set +e
  "$@" >"$tmp_log" 2>&1
  exit_code=$?
  set -e

  finished_at="$(date -u +'%Y-%m-%dT%H:%M:%SZ')"
  finish_epoch="$(date -u +%s)"
  duration=$((finish_epoch - start_epoch))

  if [[ "$exit_code" -eq 0 ]]; then
    status="PASS"
  else
    status="FAIL"
  fi

  {
    printf '\n===== %s command=%q status=%s exit=%s duration=%ss =====\n' "$finished_at" "$*" "$status" "$exit_code" "$duration"
    cat "$tmp_log"
  } >> "$LOG_FILE"

  jq -n \
    --arg command "$*" \
    --arg status "$status" \
    --arg started_at "$started_at" \
    --arg finished_at "$finished_at" \
    --arg log_file "$LOG_FILE" \
    --argjson exit_code "$exit_code" \
    --argjson duration_sec "$duration" \
    --argjson tail_lines "$TAIL_LINES" \
    --rawfile log_tail <(tail -n "$TAIL_LINES" "$tmp_log") \
    '{
      command: $command,
      status: $status,
      exit_code: $exit_code,
      started_at: $started_at,
      finished_at: $finished_at,
      duration_sec: $duration_sec,
      log_file: $log_file,
      tail_lines: $tail_lines,
      log_tail: $log_tail
    }' > "$STAMP_FILE"

  rm -f "$tmp_log"

  cat "$STAMP_FILE"
  exit "$exit_code"
}

main "$@"
