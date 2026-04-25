#!/usr/bin/env bash
set -Eeuo pipefail

SPOT_UI_SCRIPT="${SPOT_UI_SCRIPT:-/home/ogre/spot-stack/watch/spot-ui-01.sh}"
SPOT_UI_STATE_DIR="${SPOT_UI_STATE_DIR:-/home/ogre/spot-stack/watch/state}"
SPOT_UI_HISTORY_FILE="${SPOT_UI_HISTORY_FILE:-${SPOT_UI_STATE_DIR}/spot-ui-history.jsonl}"
SPOT_UI_HISTORY_LIMIT="${SPOT_UI_HISTORY_LIMIT:-120}"

need_file(){ [[ -f "$1" ]] || { echo "ERROR: missing file: $1" >&2; exit 2; }; }
need_cmd(){ command -v "$1" >/dev/null 2>&1 || { echo "ERROR: missing command: $1" >&2; exit 2; }; }

capture(){
  need_file "$SPOT_UI_SCRIPT"
  need_cmd mkdir
  need_cmd jq
  mkdir -p "$SPOT_UI_STATE_DIR"
  bash "$SPOT_UI_SCRIPT" --json | jq -c . >> "$SPOT_UI_HISTORY_FILE"
}

trim(){
  [[ -f "$SPOT_UI_HISTORY_FILE" ]] || return 0
  local tmp
  tmp="${SPOT_UI_HISTORY_FILE}.$$"
  tail -n "$SPOT_UI_HISTORY_LIMIT" "$SPOT_UI_HISTORY_FILE" > "$tmp"
  mv "$tmp" "$SPOT_UI_HISTORY_FILE"
}

summary(){
  need_cmd jq
  if [[ ! -f "$SPOT_UI_HISTORY_FILE" ]]; then
    jq -n '{count:0, items:[], trends:{}}'
    return 0
  fi
  tail -n "$SPOT_UI_HISTORY_LIMIT" "$SPOT_UI_HISTORY_FILE" | jq -s '{
    count: length,
    first_generated_at: (.[0].generated_at // null),
    last_generated_at: (.[-1].generated_at // null),
    trends: {
      routing_violations: [.[].routing.violations],
      routing_fallbacks: [.[].routing.fallbacks],
      banner_statuses: [.[].banner.status],
      latest_banner: (.[-1].banner // null),
      workers_latest: (.[-1].workers // []),
      worker_latency: (
        [.[].workers[]? | {worker, avg_total_ms, avg_tok_per_sec}]
        | group_by(.worker)
        | map({worker: .[0].worker, avg_total_ms: [.[].avg_total_ms], avg_tok_per_sec: [.[].avg_tok_per_sec]})
      )
    },
    items: .
  }'
}

case "${1:-capture}" in
  capture) capture; trim ;;
  summary|--summary) summary ;;
  trim) trim ;;
  -h|--help|help)
    echo "Usage: $(basename "$0") [capture|summary|trim]"
    ;;
  *) echo "ERROR: unknown command: $1" >&2; exit 2 ;;
esac
