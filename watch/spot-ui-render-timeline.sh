#!/usr/bin/env bash
set -Eeuo pipefail

SPOT_UI_INCIDENTS_JSON="${SPOT_UI_INCIDENTS_JSON:-/var/www/html/spot/incidents.json}"

if [[ ! -f "$SPOT_UI_INCIDENTS_JSON" ]]; then
  printf '<div class="card"><h2>Incident Timeline</h2><p class="meta">No incidents.json feed available yet.</p></div>\n'
  exit 0
fi

jq -r '
  def safe($x): ($x // "n/a" | tostring);
  def factors($x): (($x // []) | join("; "));
  def rem($x):
    if ($x.remediation // null) == null then "n/a"
    else "<b>" + safe($x.remediation.class) + "</b> — " + safe($x.remediation.suggestion) +
         "<br><span class=\"meta\">risk=" + safe($x.remediation.risk_class) +
         " · backup_required=" + safe($x.remediation.backup_required) +
         " · autonomy=" + safe($x.remediation.autonomy) + "</span>"
    end;
  def row:
    "<tr><td>" + safe(.ts) +
    "</td><td>" + safe(.type) +
    "</td><td>" + safe(.incident_id) +
    "</td><td>" + safe(.severity) +
    "</td><td>" + safe(.ack_state) +
    "</td><td>" + safe(.remediation_state) +
    "</td><td>" + safe(.risk.level) + " (" + safe(.risk.score) + ")" +
    "</td><td>" + factors(.factors // .risk.factors) +
    "</td><td>" + rem(.) + "</td></tr>";
  def open_rows:
    ((.open_incidents // []) | if length == 0 then "<tr><td colspan=\"9\" class=\"meta\">No open incidents</td></tr>" else map(row) | join("") end);
  def recent_rows:
    ((.items // [])[-8:] | if length == 0 then "<tr><td colspan=\"9\" class=\"meta\">No incident history</td></tr>" else map(row) | join("") end);
  "<div class=\"card\"><h2>Incident Timeline</h2>" +
  "<p>Entries: " + safe(.count) + " · Latest: " + safe(.latest.ts) + " · Current: " + safe(.latest.risk.level) + " (" + safe(.latest.risk.score) + ")</p>" +
  "<h3>Open Incidents</h3><table><thead><tr><th>Timestamp</th><th>Type</th><th>ID</th><th>Severity</th><th>Ack</th><th>Remediation</th><th>Risk</th><th>Factors</th><th>Suggested Action</th></tr></thead><tbody>" + open_rows + "</tbody></table>" +
  "<h3>Recent Incident History</h3><table><thead><tr><th>Timestamp</th><th>Type</th><th>ID</th><th>Severity</th><th>Ack</th><th>Remediation</th><th>Risk</th><th>Factors</th><th>Suggested Action</th></tr></thead><tbody>" + recent_rows + "</tbody></table></div>"
' "$SPOT_UI_INCIDENTS_JSON"
