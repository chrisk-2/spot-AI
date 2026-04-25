#!/usr/bin/env bash
set -Eeuo pipefail

SPOT_UI_RISK_RENDERER="${SPOT_UI_RISK_RENDERER:-/home/ogre/spot-stack/watch/spot-ui-render-risk.sh}"
SPOT_UI_STATE_DIR="${SPOT_UI_STATE_DIR:-/home/ogre/spot-stack/watch/state}"
SPOT_UI_LEDGER_FILE="${SPOT_UI_LEDGER_FILE:-${SPOT_UI_STATE_DIR}/spot-ui-incidents.jsonl}"
SPOT_UI_LEDGER_LIMIT="${SPOT_UI_LEDGER_LIMIT:-200}"

need_file(){ [[ -f "$1" ]] || { echo "ERROR: missing file: $1" >&2; exit 2; }; }
need_cmd(){ command -v "$1" >/dev/null 2>&1 || { echo "ERROR: missing command: $1" >&2; exit 2; }; }

capture(){
  need_file "$SPOT_UI_RISK_RENDERER"
  need_cmd jq
  need_cmd mkdir
  mkdir -p "$SPOT_UI_STATE_DIR"

  local risk prev_level curr_level ts
  ts="$(date -u +'%Y-%m-%dT%H:%M:%SZ')"
  risk="$(bash "$SPOT_UI_RISK_RENDERER")"
  curr_level="$(jq -r '.level // "UNKNOWN"' <<<"$risk")"
  prev_level="NONE"
  [[ -f "$SPOT_UI_LEDGER_FILE" ]] && prev_level="$(tail -n 1 "$SPOT_UI_LEDGER_FILE" | jq -r '.risk.level // "NONE"' 2>/dev/null || echo NONE)"

  if [[ "$curr_level" != "NORMAL" || "$curr_level" != "$prev_level" ]]; then
    jq -c -n --arg ts "$ts" --arg prev "$prev_level" --argjson risk "$risk" \
      '{ts:$ts,type:(if $risk.level==$prev then "risk_observation" else "risk_transition" end),previous_level:$prev,risk:$risk}' >> "$SPOT_UI_LEDGER_FILE"
  fi
}

trim(){
  [[ -f "$SPOT_UI_LEDGER_FILE" ]] || return 0
  local tmp="${SPOT_UI_LEDGER_FILE}.$$"
  tail -n "$SPOT_UI_LEDGER_LIMIT" "$SPOT_UI_LEDGER_FILE" > "$tmp"
  mv "$tmp" "$SPOT_UI_LEDGER_FILE"
}

summary(){
  need_cmd jq
  if [[ ! -f "$SPOT_UI_LEDGER_FILE" ]]; then
    jq -n '{count:0,latest:null,items:[]}'
    return 0
  fi
  tail -n "$SPOT_UI_LEDGER_LIMIT" "$SPOT_UI_LEDGER_FILE" | jq -s '{count:length,latest:.[-1],transitions:[.[]|select(.type=="risk_transition")],items:.}'
}

case "${1:-capture}" in
  capture) capture; trim ;;
  summary|--summary) summary ;;
  trim) trim ;;
  -h|--help|help) echo "Usage: $(basename "$0") [capture|summary|trim]" ;;
  *) echo "ERROR: unknown command: $1" >&2; exit 2 ;;
esac
