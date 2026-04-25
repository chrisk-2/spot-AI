#!/usr/bin/env bash
set -Eeuo pipefail

SPOT_UI_STATE_DIR="${SPOT_UI_STATE_DIR:-/home/ogre/spot-stack/watch/state}"
SPOT_UI_ACK_FILE="${SPOT_UI_ACK_FILE:-${SPOT_UI_STATE_DIR}/spot-ui-acks.jsonl}"
SPOT_UI_ACK_LIMIT="${SPOT_UI_ACK_LIMIT:-200}"

need_cmd(){ command -v "$1" >/dev/null 2>&1 || { echo "ERROR: missing command: $1" >&2; exit 2; }; }
usage(){ echo "Usage: $(basename "$0") add <risk-level|incident-id> <status> <note...> | summary | trim"; }

add_ack(){
  need_cmd jq
  mkdir -p "$SPOT_UI_STATE_DIR"
  local target="${1:-}" status="${2:-}"; shift 2 || true
  local note="$*" ts
  [[ -n "$target" && -n "$status" && -n "$note" ]] || { usage >&2; exit 2; }
  ts="$(date -u +'%Y-%m-%dT%H:%M:%SZ')"
  jq -c -n --arg ts "$ts" --arg target "$target" --arg status "$status" --arg note "$note" \
    '{ts:$ts,target:$target,status:$status,note:$note}' >> "$SPOT_UI_ACK_FILE"
}

trim(){
  [[ -f "$SPOT_UI_ACK_FILE" ]] || return 0
  local tmp="${SPOT_UI_ACK_FILE}.$$"
  tail -n "$SPOT_UI_ACK_LIMIT" "$SPOT_UI_ACK_FILE" > "$tmp"
  mv "$tmp" "$SPOT_UI_ACK_FILE"
}

summary(){
  need_cmd jq
  if [[ ! -f "$SPOT_UI_ACK_FILE" ]]; then
    jq -n '{count:0,latest:null,items:[]}'
    return 0
  fi
  tail -n "$SPOT_UI_ACK_LIMIT" "$SPOT_UI_ACK_FILE" | jq -s '{count:length,latest:.[-1],items:.}'
}

case "${1:-}" in
  add) shift; add_ack "$@"; trim ;;
  summary|--summary) summary ;;
  trim) trim ;;
  -h|--help|help|"") usage ;;
  *) echo "ERROR: unknown command: $1" >&2; usage >&2; exit 2 ;;
esac
