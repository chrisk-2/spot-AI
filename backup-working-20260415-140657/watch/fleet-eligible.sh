#!/usr/bin/env bash
set -euo pipefail

STATE_FILE="/home/ogre/spot-stack/watch/state/fleet-status.json"

[[ -f "$STATE_FILE" ]] || {
  echo "state file not found: $STATE_FILE" >&2
  exit 1
}

jq -r '
  .hosts
  | to_entries
  | map(select(.value.eligible == true))
  | .[].key
' "$STATE_FILE"
