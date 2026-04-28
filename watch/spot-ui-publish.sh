#!/usr/bin/env bash
set -Eeuo pipefail

SPOT_UI_SCRIPT="${SPOT_UI_SCRIPT:-/home/ogre/spot-stack/watch/spot-ui-01.sh}"
SPOT_UI_HISTORY_SCRIPT="${SPOT_UI_HISTORY_SCRIPT:-/home/ogre/spot-stack/watch/spot-ui-history.sh}"
SPOT_UI_RENDER_HTML="${SPOT_UI_RENDER_HTML:-/home/ogre/spot-stack/watch/spot-ui-render-html.sh}"
SPOT_UI_INCIDENT_LEDGER="${SPOT_UI_INCIDENT_LEDGER:-/home/ogre/spot-stack/watch/spot-ui-incident-ledger.sh}"
SPOT_UI_ACK="${SPOT_UI_ACK:-/home/ogre/spot-stack/watch/spot-ui-ack.sh}"
SPOT_UI_READINESS="${SPOT_UI_READINESS:-/home/ogre/spot-stack/watch/spot-ui-readiness.sh}"
SPOT_UI_OUT_DIR="${SPOT_UI_OUT_DIR:-/var/www/html/spot}"
SPOT_UI_TMP_DIR="${SPOT_UI_TMP_DIR:-${SPOT_UI_OUT_DIR}/.tmp}"
SPOT_UI_INTERVAL="${SPOT_UI_INTERVAL:-60}"
SPOT_UI_ONCE="${SPOT_UI_ONCE:-0}"

need_file(){ [[ -f "$1" ]] || { echo "ERROR: missing file: $1" >&2; exit 2; }; }

publish_once(){
  need_file "$SPOT_UI_SCRIPT"; need_file "$SPOT_UI_HISTORY_SCRIPT"; need_file "$SPOT_UI_RENDER_HTML"; need_file "$SPOT_UI_INCIDENT_LEDGER"; need_file "$SPOT_UI_ACK"; need_file "$SPOT_UI_READINESS"
  mkdir -p "$SPOT_UI_OUT_DIR" "$SPOT_UI_TMP_DIR"
  local ts html_tmp json_tmp meta_tmp hist_tmp inc_tmp ack_tmp readiness_tmp
  ts="$(date -u +'%Y-%m-%dT%H:%M:%SZ')"
  html_tmp="${SPOT_UI_TMP_DIR}/index.html.$$"; json_tmp="${SPOT_UI_TMP_DIR}/spot.json.$$"; meta_tmp="${SPOT_UI_TMP_DIR}/meta.json.$$"; hist_tmp="${SPOT_UI_TMP_DIR}/history.json.$$"; inc_tmp="${SPOT_UI_TMP_DIR}/incidents.json.$$"; ack_tmp="${SPOT_UI_TMP_DIR}/acks.json.$$"; readiness_tmp="${SPOT_UI_TMP_DIR}/operator-readiness.json.$$"
  bash "$SPOT_UI_HISTORY_SCRIPT" capture
  bash "$SPOT_UI_SCRIPT" --json > "$json_tmp"
  bash "$SPOT_UI_HISTORY_SCRIPT" summary > "$hist_tmp"
  SPOT_UI_JSON="$json_tmp" SPOT_UI_HISTORY_JSON="$hist_tmp" bash "$SPOT_UI_INCIDENT_LEDGER" capture
  bash "$SPOT_UI_INCIDENT_LEDGER" summary > "$inc_tmp"
  bash "$SPOT_UI_ACK" summary > "$ack_tmp"
  bash "$SPOT_UI_READINESS" > "$readiness_tmp"
  SPOT_UI_JSON="$json_tmp" SPOT_UI_HISTORY_JSON="$hist_tmp" SPOT_UI_INCIDENTS_JSON="$inc_tmp" SPOT_UI_ACKS_JSON="$ack_tmp" SPOT_UI_READINESS_JSON="$readiness_tmp" bash "$SPOT_UI_RENDER_HTML" > "$html_tmp"
  jq -n \
    --arg published_at "$ts" \
    --arg source "$SPOT_UI_SCRIPT" \
    '{
      published_at: $published_at,
      source: $source,
      feeds: [
        "spot.json",
        "history.json",
        "incidents.json",
        "acks.json",
        "operator-readiness.json",
        "meta.json"
      ]
    }' > "$meta_tmp"
  mv "$html_tmp" "${SPOT_UI_OUT_DIR}/index.html"; mv "$json_tmp" "${SPOT_UI_OUT_DIR}/spot.json"; mv "$hist_tmp" "${SPOT_UI_OUT_DIR}/history.json"; mv "$inc_tmp" "${SPOT_UI_OUT_DIR}/incidents.json"; mv "$ack_tmp" "${SPOT_UI_OUT_DIR}/acks.json"; mv "$readiness_tmp" "${SPOT_UI_OUT_DIR}/operator-readiness.json"; mv "$meta_tmp" "${SPOT_UI_OUT_DIR}/meta.json"
  echo "published spot dashboard set at ${ts}"
}

case "${1:-}" in once|--once) SPOT_UI_ONCE=1 ;; loop|--loop|"") ;; *) ;; esac
if [[ "$SPOT_UI_ONCE" = 1 ]]; then publish_once; exit 0; fi
while true; do publish_once || true; sleep "$SPOT_UI_INTERVAL"; done
