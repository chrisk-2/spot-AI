#!/usr/bin/env bash
set -euo pipefail

BASE="$HOME/spot-stack"
UI="$BASE/starfleet-ui"

"$BASE/watch/starfleet-online-check.sh" quiet

mkdir -p "$UI/public"
cp "$BASE/watch/state/starfleet-online-check.json" "$UI/public/status.json"

if [[ -d "$UI/dist" ]]; then
  cp "$BASE/watch/state/starfleet-online-check.json" "$UI/dist/status.json"
fi
