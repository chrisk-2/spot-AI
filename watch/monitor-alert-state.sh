#!/usr/bin/env bash
set -Eeuo pipefail

BASE_DIR="${BASE_DIR:-/home/ogre/spot-stack/watch}"
STATE_DIR="${STATE_DIR:-${BASE_DIR}/state}"
HISTORY_DIR="${HISTORY_DIR:-${STATE_DIR}/history}"
SPOT_OPS="${SPOT_OPS:-${BASE_DIR}/spot-ops.sh}"

LATEST_STATUS_FILE="${LATEST_STATUS_FILE:-${HISTORY_DIR}/monitor-alert-latest.json}"
TRANSITIONS_FILE="${TRANSITIONS_FILE:-${HISTORY_DIR}/monitor-alert-transitions.jsonl}"

mkdir -p "${HISTORY_DIR}"

if [[ ! -x "${SPOT_OPS}" ]]; then
  echo "ERROR: spot-ops.sh missing or not executable: ${SPOT_OPS}" >&2
  exit 2
fi

need_cmd() {
  local cmd="$1"
  command -v "$cmd" >/dev/null 2>&1 || {
    echo "ERROR: required command not found: $cmd" >&2
    exit 2
  }
}

need_cmd jq

ALERTS_JSON="$("${SPOT_OPS}" monitor-alerts | sed '/^=== /d')"

echo "${ALERTS_JSON}" | jq empty >/dev/null 2>&1 || {
  echo "ERROR: monitor-alerts did not return valid JSON" >&2
  exit 2
}

NEW_STATUS="$(echo "${ALERTS_JSON}" | jq -r '.status')"
NEW_TS="$(echo "${ALERTS_JSON}" | jq -r '.timestamp')"

PREV_STATUS=""
PREV_TS=""
if [[ -f "${LATEST_STATUS_FILE}" ]]; then
  PREV_STATUS="$(jq -r '.status // empty' "${LATEST_STATUS_FILE}" 2>/dev/null || true)"
  PREV_TS="$(jq -r '.timestamp // empty' "${LATEST_STATUS_FILE}" 2>/dev/null || true)"
fi

TMP_FILE="$(mktemp)"
echo "${ALERTS_JSON}" | jq \
  --arg writer "monitor-alert-state.sh" \
  '. + {writer:$writer}' > "${TMP_FILE}"
command mv -f "${TMP_FILE}" "${LATEST_STATUS_FILE}"

jq -cn \
  --arg timestamp "${NEW_TS}" \
  --arg status "${NEW_STATUS}" \
  --arg previous_status "${PREV_STATUS}" \
  --arg previous_timestamp "${PREV_TS}" \
  --arg latest_status_file "${LATEST_STATUS_FILE}" \
  --arg source "spot-ops.sh monitor-alerts" \
  '{
    timestamp: $timestamp,
    status: $status,
    previous_status: (if $previous_status == "" then null else $previous_status end),
    previous_timestamp: (if $previous_timestamp == "" then null else $previous_timestamp end),
    latest_status_file: $latest_status_file,
    source: $source
  }' >> "${TRANSITIONS_FILE}"
printf '\n' >> "${TRANSITIONS_FILE}"

if [[ "${NEW_STATUS}" != "${PREV_STATUS}" ]]; then
  echo "${NEW_TS} TRANSITION ${PREV_STATUS:-NONE} -> ${NEW_STATUS}"
else
  echo "${NEW_TS} NO_CHANGE ${NEW_STATUS}"
fi
