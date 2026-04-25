#!/usr/bin/env bash
set -Eeuo pipefail

SPOT_UI_ACKS_JSON="${SPOT_UI_ACKS_JSON:-/var/www/html/spot/acks.json}"

if [[ ! -f "$SPOT_UI_ACKS_JSON" ]]; then
  printf '<div class="card"><h2>Operator Acknowledgements</h2><p class="meta">No acknowledgements recorded.</p></div>\n'
  exit 0
fi

jq -r '
  def safe($x): ($x // "n/a" | tostring);
  def row:
    "<tr><td>" + safe(.ts) + "</td><td>" + safe(.target) + "</td><td>" + safe(.status) + "</td><td>" + safe(.note) + "</td></tr>";
  "<div class=\"card\"><h2>Operator Acknowledgements</h2>" +
  "<p>Entries: " + safe(.count) + " · Latest: " + safe(.latest.ts) + " · Status: " + safe(.latest.status) + "</p>" +
  "<table><thead><tr><th>Timestamp</th><th>Target</th><th>Status</th><th>Note</th></tr></thead><tbody>" +
  ((.items // [])[-5:] | map(row) | join("")) +
  "</tbody></table>" +
  "<p class=\"meta\">Add note: <code>spot-ui-ack.sh add HIGH investigating your note here</code></p></div>"
' "$SPOT_UI_ACKS_JSON"
