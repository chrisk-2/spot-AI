#!/usr/bin/env bash
set -Eeuo pipefail

SPOT_UI_INCIDENTS_JSON="${SPOT_UI_INCIDENTS_JSON:-/var/www/html/spot/incidents.json}"

if [[ ! -f "$SPOT_UI_INCIDENTS_JSON" ]]; then
  printf '<div class="card"><h2>Incident Timeline</h2><p class="meta">No incidents.json feed available yet.</p></div>\n'
  exit 0
fi

jq -r '
  def safe($x): ($x // "n/a" | tostring);
  def row:
    "<tr><td>" + safe(.ts) + "</td><td>" + safe(.type) + "</td><td>" + safe(.previous_level) + "</td><td>" + safe(.risk.level) + "</td><td>" + safe(.risk.score) + "</td><td>" + ((.risk.factors // []) | join("; ")) + "</td></tr>";
  "<div class=\"card\"><h2>Incident Timeline</h2>" +
  "<p>Entries: " + safe(.count) + " · Latest: " + safe(.latest.ts) + " · Current: " + safe(.latest.risk.level) + " (" + safe(.latest.risk.score) + ")</p>" +
  "<table><thead><tr><th>Timestamp</th><th>Type</th><th>Previous</th><th>Level</th><th>Score</th><th>Factors</th></tr></thead><tbody>" +
  ((.items // [])[-5:] | map(row) | join("")) +
  "</tbody></table></div>"
' "$SPOT_UI_INCIDENTS_JSON"
