#!/usr/bin/env bash
set -euo pipefail

STATE_FILE="/home/ogre/spot-stack/watch/state/fleet-status.json"
REQUIRED_MODEL="${1:-}"

[[ -n "$REQUIRED_MODEL" ]] || {
  echo "usage: $0 <model-name>" >&2
  exit 1
}

[[ -f "$STATE_FILE" ]] || {
  echo "state file not found: $STATE_FILE" >&2
  exit 1
}

jq -r --arg model "$REQUIRED_MODEL" '
  .hosts
  | to_entries
  | map(
      select(
        .value.eligible == true
        and (.value.models | index($model))
      )
    )
  | .[0].key // empty
' "$STATE_FILE"
