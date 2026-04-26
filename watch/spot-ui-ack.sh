#!/usr/bin/env bash
set -Eeuo pipefail

SPOT_UI_STATE_DIR="${SPOT_UI_STATE_DIR:-/home/ogre/spot-stack/watch/state}"
SPOT_UI_ACK_FILE="${SPOT_UI_ACK_FILE:-${SPOT_UI_STATE_DIR}/spot-ui-acks.jsonl}"
SPOT_UI_INCIDENT_FILE="${SPOT_UI_INCIDENT_FILE:-${SPOT_UI_STATE_DIR}/spot-ui-incidents.jsonl}"
SPOT_UI_ENGINE_STATE_FILE="${SPOT_UI_ENGINE_STATE_FILE:-${SPOT_UI_STATE_DIR}/incident-engine-state.json}"
SPOT_UI_ACK_LIMIT="${SPOT_UI_ACK_LIMIT:-200}"

need_cmd(){ command -v "$1" >/dev/null 2>&1 || { echo "ERROR: missing command: $1" >&2; exit 2; }; }
usage(){ echo "Usage: $(basename "$0") add <risk-level|incident-id> <acknowledged|resolved|note> <note...> | summary | trim"; }

normalize_status(){
  case "${1:-}" in
    ack|acknowledge|acknowledged) printf 'acknowledged' ;;
    resolve|resolved|close|closed) printf 'resolved' ;;
    note|observed|info) printf 'note' ;;
    *) printf '%s' "$1" ;;
  esac
}

rewrite_incidents_for_ack(){
  local target="$1" status="$2" ts="$3" note="$4"
  [[ -f "$SPOT_UI_INCIDENT_FILE" ]] || return 0
  [[ "$target" =~ ^INC-[0-9]+$ ]] || return 0
  local tmp="${SPOT_UI_INCIDENT_FILE}.$$"
  jq -c --arg target "$target" --arg status "$status" --arg ts "$ts" --arg note "$note" '
    if (.incident_id // "") == $target then
      .ack_state = $status
      | .ack_ts = $ts
      | .ack_note = $note
      | if $status == "resolved" then .remediation_state = "closed" else . end
    else . end
  ' "$SPOT_UI_INCIDENT_FILE" > "$tmp"
  mv "$tmp" "$SPOT_UI_INCIDENT_FILE"
}

clear_resolved_signature(){
  local target="$1" status="$2"
  [[ "$status" == "resolved" ]] || return 0
  [[ -f "$SPOT_UI_ENGINE_STATE_FILE" ]] || return 0
  [[ "$target" =~ ^INC-[0-9]+$ ]] || return 0
  local tmp="${SPOT_UI_ENGINE_STATE_FILE}.$$"
  jq -c --arg target "$target" '
    .open_signatures = ((.open_signatures // {}) | with_entries(select(.value != $target)))
  ' "$SPOT_UI_ENGINE_STATE_FILE" > "$tmp"
  mv "$tmp" "$SPOT_UI_ENGINE_STATE_FILE"
}

add_ack(){
  need_cmd jq
  mkdir -p "$SPOT_UI_STATE_DIR"
  local target="${1:-}" raw_status="${2:-}"; shift 2 || true
  local status note ts
  status="$(normalize_status "$raw_status")"
  note="$*"
  [[ -n "$target" && -n "$status" && -n "$note" ]] || { usage >&2; exit 2; }
  ts="$(date -u +'%Y-%m-%dT%H:%M:%SZ')"
  jq -c -n --arg ts "$ts" --arg target "$target" --arg status "$status" --arg note "$note" \
    '{ts:$ts,target:$target,status:$status,note:$note}' >> "$SPOT_UI_ACK_FILE"
  rewrite_incidents_for_ack "$target" "$status" "$ts" "$note"
  clear_resolved_signature "$target" "$status"
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
