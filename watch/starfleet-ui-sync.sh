#!/usr/bin/env bash
set -euo pipefail

BASE="$HOME/spot-stack"
UI="$BASE/starfleet-ui"
STATE="$BASE/watch/state/starfleet-online-check.json"

# The online check exits non-zero when monitored hosts are down.
# That is valid status data, not a UI-sync service failure.
set +e
"$BASE/watch/starfleet-online-check.sh" quiet
CHECK_RC=$?
set -e

if [[ ! -s "$STATE" ]]; then
  echo "ERROR: missing online-check state file: $STATE" >&2
  exit 1
fi

mkdir -p "$UI/public"
cp "$STATE" "$UI/public/status.json"

if [[ -d "$UI/dist" ]]; then
  cp "$STATE" "$UI/dist/status.json"
fi

echo "starfleet-ui-sync: published status.json check_rc=$CHECK_RC"
exit 0
