#!/usr/bin/env bash
set -Eeuo pipefail

SPOT_UI_JSON="${SPOT_UI_JSON:-/var/www/html/spot/spot.json}"
SPOT_UI_HISTORY_JSON="${SPOT_UI_HISTORY_JSON:-/var/www/html/spot/history.json}"
SPOT_UI_INCIDENTS_JSON="${SPOT_UI_INCIDENTS_JSON:-/var/www/html/spot/incidents.json}"
SPOT_UI_ACKS_JSON="${SPOT_UI_ACKS_JSON:-/var/www/html/spot/acks.json}"
REMEDIATION_STATE_FILE="${REMEDIATION_STATE_FILE:-/home/ogre/spot-stack/watch/state/remediation-state.json}"
RISK_RENDERER="${RISK_RENDERER:-/home/ogre/spot-stack/watch/spot-ui-render-risk.sh}"
TIMELINE_RENDERER="${TIMELINE_RENDERER:-/home/ogre/spot-stack/watch/spot-ui-render-timeline.sh}"
ACK_RENDERER="${ACK_RENDERER:-/home/ogre/spot-stack/watch/spot-ui-render-acks.sh}"
STALE_SNAPSHOT_SECONDS="${STALE_SNAPSHOT_SECONDS:-180}"
HISTORY_SPARK_LIMIT="${HISTORY_SPARK_LIMIT:-20}"

need_file(){ [[ -f "$1" ]] || { echo "ERROR: missing file: $1" >&2; exit 2; }; }
need_cmd(){ command -v "$1" >/dev/null 2>&1 || { echo "ERROR: missing command: $1" >&2; exit 2; }; }

need_cmd jq
need_file "$SPOT_UI_JSON"
need_file "$RISK_RENDERER"

TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT

cp "$SPOT_UI_JSON" "$TMPDIR/spot.json"
if [[ -f "$SPOT_UI_HISTORY_JSON" ]]; then cp "$SPOT_UI_HISTORY_JSON" "$TMPDIR/history.json"; else printf '{"count":0,"trends":{}}' > "$TMPDIR/history.json"; fi
if [[ -f "$REMEDIATION_STATE_FILE" ]]; then cp "$REMEDIATION_STATE_FILE" "$TMPDIR/remediation.json"; else printf '{}' > "$TMPDIR/remediation.json"; fi

SPOT_UI_JSON="$SPOT_UI_JSON" SPOT_UI_HISTORY_JSON="$SPOT_UI_HISTORY_JSON" REMEDIATION_STATE_FILE="$REMEDIATION_STATE_FILE" STALE_SNAPSHOT_SECONDS="$STALE_SNAPSHOT_SECONDS" bash "$RISK_RENDERER" > "$TMPDIR/risk.json"

timeline_card='<div class="card"><h2>Incident Timeline</h2><p class="meta">Timeline renderer unavailable.</p></div>'
if [[ -f "$TIMELINE_RENDERER" ]]; then
  timeline_card="$(SPOT_UI_INCIDENTS_JSON="$SPOT_UI_INCIDENTS_JSON" bash "$TIMELINE_RENDERER" || printf '%s' '<div class="card"><h2>Incident Timeline</h2><p class="meta">Timeline render failed.</p></div>')"
fi

ack_card='<div class="card"><h2>Operator Acknowledgements</h2><p class="meta">Acknowledgement renderer unavailable.</p></div>'
if [[ -f "$ACK_RENDERER" ]]; then
  ack_card="$(SPOT_UI_ACKS_JSON="$SPOT_UI_ACKS_JSON" bash "$ACK_RENDERER" || printf '%s' '<div class="card"><h2>Operator Acknowledgements</h2><p class="meta">Acknowledgement render failed.</p></div>')"
fi

jq -r -n \
  --slurpfile sf "$TMPDIR/spot.json" \
  --slurpfile hf "$TMPDIR/history.json" \
  --slurpfile rf "$TMPDIR/remediation.json" \
  --slurpfile kf "$TMPDIR/risk.json" \
  --arg timeline "$timeline_card" \
  --arg ack "$ack_card" \
  --argjson stale "$STALE_SNAPSHOT_SECONDS" \
  --argjson spark_limit "$HISTORY_SPARK_LIMIT" '
  $sf[0] as $s |
  $hf[0] as $h |
  $rf[0] as $r |
  $kf[0] as $k |
  def safe($x): ($x // "n/a" | tostring);
  def cls($x): ($x|ascii_downcase);
  def lastn($a; $n): ($a // [] | if length > $n then .[(length-$n):] else . end);
  def spark($a): (lastn($a; $spark_limit) | map(if . == null then "·" else tostring end) | join(" "));
  def increasing($a): ($a|length) >= 3 and ($a[-1] > $a[-2]) and ($a[-2] > $a[-3]);
  def age_sec: ((now | floor) - (($h.last_generated_at // $s.generated_at) | fromdateiso8601? // (now|floor)));
  def nonok_count: (($h.trends.banner_statuses // []) | lastn(.;5) | map(select(. != "OK")) | length);
  def rem_entries: ($r | to_entries | map(select(.key != "_meta")));
  def anomaly_list:[(if age_sec > $stale then "publisher/history feed stale: "+(age_sec|tostring)+"s since latest snapshot" else empty end),(if increasing($h.trends.routing_fallbacks // []) then "routing fallbacks rising for 3 consecutive snapshots" else empty end),(if increasing($h.trends.routing_violations // []) then "routing violations rising for 3 consecutive snapshots" else empty end),(if nonok_count >= 3 then "banner non-OK in "+(nonok_count|tostring)+" of last 5 snapshots" else empty end),(($h.trends.worker_latency // [])[]? | select((.avg_total_ms // [] | lastn(.;3) | increasing(.))) | "latency rising on "+.worker),(rem_entries[]? | select(.value.quarantined == true) | "remediation active quarantine on "+.key),(rem_entries[]? | select((.value.violation_count_window // 0) > 0) | "remediation remembers routing violations on "+.key)];
  def incidents: if (($s.banner.incidents // [])|length)==0 then "<li>No active incidents</li>" else (($s.banner.incidents // []) | map("<li>"+. +"</li>") | join("")) end;
  def risk_html: if (($k.factors // [])|length)==0 then "<li>No risk factors active</li>" else (($k.factors // []) | map("<li>"+. +"</li>") | join("")) end;
  def anomalies_html: if (anomaly_list|length)==0 then "<li>No anomalies detected</li>" else (anomaly_list | map("<li>"+. +"</li>") | join("")) end;
  def worker_fail_count: (($s.workers // []) | map(select(.ok != true)) | length);
  def endpoint_fail_count: ($s.endpoints.fail_count // 0);
  def latest_route_violations: ((lastn(($h.trends.routing_violations // []); 1)[0]) // 0);
  def latest_route_fallbacks: ((lastn(($h.trends.routing_fallbacks // []); 1)[0]) // 0);
  def integrity_class: if latest_route_violations == 0 and latest_route_fallbacks == 0 and nonok_count == 0 then "ok" elif latest_route_violations == 0 then "warn" else "fail" end;
  def control_class: if worker_fail_count == 0 and endpoint_fail_count == 0 and age_sec <= $stale then "ok" elif age_sec <= ($stale * 2) then "warn" else "fail" end;
  def safety_class: if (($k.score // 0) == 0 and worker_fail_count == 0 and (($r._meta.last_audit_violations // 0) == 0)) then "ok" elif (($k.score // 0) < 5) then "warn" else "fail" end;
  def readiness_strip:
    "<div class=\"grid\">"+
    "<div class=\"card\"><h2>Fleet Integrity: <span class=\""+integrity_class+"\">"+(integrity_class|ascii_upcase)+"</span></h2><p>Latest route violations: <b>"+(latest_route_violations|tostring)+"</b></p><p>Latest fallbacks: <b>"+(latest_route_fallbacks|tostring)+"</b></p><p class=\"meta\">Banner non-OK count, last 5: "+(nonok_count|tostring)+"</p></div>"+
    "<div class=\"card\"><h2>Control Surface: <span class=\""+control_class+"\">"+(control_class|ascii_upcase)+"</span></h2><p>Worker failures: <b>"+(worker_fail_count|tostring)+"</b></p><p>Endpoint failures: <b>"+(endpoint_fail_count|tostring)+"</b></p><p class=\"meta\">History age: "+(age_sec|tostring)+"s</p></div>"+
    "<div class=\"card\"><h2>Backup / Safety Gate: <span class=\""+safety_class+"\">"+(safety_class|ascii_upcase)+"</span></h2><p>Fleet risk score: <b>"+(($k.score // 0)|tostring)+"</b></p><p>Audit violations: <b>"+safe($r._meta.last_audit_violations)+"</b></p><p class=\"meta\">Policy: no backup, no change</p></div>"+
    "</div>";
  def worker_rows: ($s.workers // []) | map("<tr class=\""+.severity+"\"><td>"+.worker+"</td><td>"+.role+"</td><td>"+(if .ok then "OK" else "FAIL" end)+"</td><td>"+.severity+"</td><td>"+(.eligible|tostring)+"</td><td>"+(.quarantined|tostring)+"</td><td>"+(.degraded|tostring)+"</td><td>"+(.running_jobs|tostring)+"</td><td>"+safe(.avg_total_ms)+"</td><td>"+safe(.avg_tok_per_sec)+"</td></tr>") | join("");
  def remediation_rows: rem_entries | map("<tr class=\""+(if .value.quarantined then "warn" else "ok" end)+"\"><td>"+.key+"</td><td>"+safe(.value.quarantined)+"</td><td>"+safe(.value.reason)+"</td><td>"+safe(.value.fallback_count_window)+"</td><td>"+safe(.value.violation_count_window)+"</td><td>"+safe(.value.last_route_class)+"</td><td>"+safe(.value.last_updated_by)+"</td><td>"+safe(.value.last_updated_ts)+"</td></tr>") | join("");
  def latency_rows: (($h.trends.worker_latency // []) | map("<tr><td>"+.worker+"</td><td><code>"+spark(.avg_total_ms)+"</code></td><td><code>"+spark(.avg_tok_per_sec)+"</code></td></tr>") | join(""));
"<!doctype html><html><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\"><meta http-equiv=\"refresh\" content=\"60\"><title>Spot UI Cockpit</title><style>:root{--bg:#05060c;--panel:#101426;--panel2:#15192d;--line:#2d3658;--text:#f2f5ff;--muted:#aeb6d4;--orange:#ff9f40;--peach:#ffcc99;--purple:#b48cff;--blue:#72d7ff;--ok:#7ee787;--warn:#ffd166;--fail:#ff6b6b}*{box-sizing:border-box}body{font-family:system-ui,Segoe UI,sans-serif;background:radial-gradient(circle at top left,#141933 0,#05060c 45%,#02030a 100%);color:var(--text);margin:0;padding:1.25rem 1.5rem 2rem 6.5rem;min-height:100vh}body:before{content:"";position:fixed;left:0;top:0;bottom:0;width:5.25rem;background:linear-gradient(180deg,var(--orange) 0 13%,#0000 13% 16%,var(--purple) 16% 32%,#0000 32% 35%,var(--peach) 35% 58%,#0000 58% 62%,var(--blue) 62% 78%,#0000 78% 82%,var(--orange) 82% 100%);border-right:12px solid #05060c;border-radius:0 0 3rem 0;z-index:-1}h1{margin:0 0 1rem;font-size:clamp(2rem,4vw,4.25rem);letter-spacing:.08em;text-transform:uppercase;color:var(--peach);line-height:.95}h1:after{content:" / OPERATOR READY";display:block;font-size:.34em;color:var(--blue);letter-spacing:.16em;margin-top:.35rem}h2{margin:.1rem 0 .75rem;font-size:1rem;letter-spacing:.08em;text-transform:uppercase}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:1rem}.card,.banner{background:linear-gradient(180deg,var(--panel),var(--panel2));border:1px solid var(--line);border-left:1.15rem solid var(--orange);border-radius:0 1.75rem 1.75rem 0;padding:1rem 1.15rem;margin:1rem 0;box-shadow:0 0 0 1px #000 inset,0 12px 30px #0008}.grid>.card:nth-child(2n){border-left-color:var(--purple)}.grid>.card:nth-child(3n){border-left-color:var(--blue)}.banner{border-left-color:var(--peach)}.banner.ok{background:linear-gradient(180deg,#082417,#101b2d)}.banner.warn{background:linear-gradient(180deg,#332707,#15192d)}.banner.alert{background:linear-gradient(180deg,#351014,#15192d)}table{border-collapse:separate;border-spacing:0;width:100%;font-size:.95rem;overflow:hidden;border-radius:.75rem}th,td{border-bottom:1px solid var(--line);padding:.55rem .6rem;text-align:left;vertical-align:top}th{color:var(--peach);font-size:.78rem;text-transform:uppercase;letter-spacing:.08em;background:#080b17}td{background:#0d1120}.ok,.normal{color:var(--ok)}.warn,.elevated{color:var(--warn)}.fail,.alert,.critical,.high{color:var(--fail)}.meta{color:var(--muted)}tr.warn td{background:#211b0c}tr.fail td{background:#260d12}code{color:var(--blue);white-space:normal}.card p{margin:.45rem 0}.card b{font-size:1.1rem;color:var(--text)}ul{padding-left:1.2rem}@media(max-width:760px){body{padding:1rem}body:before{display:none}.card,.banner{border-left-width:.55rem;border-radius:0 1.1rem 1.1rem 0}}</style></head><body>"+
"<h1>Spot UI Cockpit</h1>"+
readiness_strip+
"<div class=\"banner "+cls($s.banner.status)+"\"><h2>Incident Banner: <span class=\""+cls($s.banner.status)+"\">"+$s.banner.status+"</span></h2><ul>"+incidents+"</ul></div>"+
"<div class=\"card\"><h2>Fleet Risk: <span class=\""+cls($k.level)+"\">"+$k.level+"</span> ("+($k.score|tostring)+")</h2><ul>"+risk_html+"</ul></div>"+
$timeline+
$ack+
"<div class=\"grid\"><div class=\"card\"><h2>Anomalies</h2><ul>"+anomalies_html+"</ul><p class=\"meta\">History age: "+(age_sec|tostring)+"s</p></div><div class=\"card\"><h2>Autonomy / remediation state</h2><p class=\"meta\">last_run_ts="+safe($r._meta.last_run_ts)+" · audit violations="+safe($r._meta.last_audit_violations)+"</p><table><thead><tr><th>Worker</th><th>Q</th><th>Reason</th><th>Fb</th><th>Vi</th><th>Route</th><th>By</th><th>TS</th></tr></thead><tbody>"+remediation_rows+"</tbody></table></div></div>"+
"<div class=\"card\"><h2>Workers</h2><table><thead><tr><th>Worker</th><th>Role</th><th>Status</th><th>Severity</th><th>Eligible</th><th>Quarantine</th><th>Degraded</th><th>Jobs</th><th>Avg ms</th><th>Tok/s</th></tr></thead><tbody>"+worker_rows+"</tbody></table></div>"+
"<div class=\"card\"><h2>Trends (last "+($spark_limit|tostring)+" snapshots)</h2><p>Snapshots: "+safe($h.count)+" · First: "+safe($h.first_generated_at)+" · Last: "+safe($h.last_generated_at)+"</p><p>Routing violations: <code>"+spark($h.trends.routing_violations)+"</code></p><p>Routing fallbacks: <code>"+spark($h.trends.routing_fallbacks)+"</code></p><p>Banner statuses: <code>"+(lastn(($h.trends.banner_statuses // []); $spark_limit) | join(" "))+"</code></p></div>"+
"<div class=\"card\"><h2>Worker latency history (last "+($spark_limit|tostring)+")</h2><table><thead><tr><th>Worker</th><th>Avg total ms</th><th>Tok/s</th></tr></thead><tbody>"+latency_rows+"</tbody></table></div>"+
"<p class=\"meta\">Generated: "+safe($s.generated_at)+" · Feeds: <code>spot.json</code> <code>history.json</code> <code>incidents.json</code> <code>acks.json</code> <code>meta.json</code></p></body></html>"
'
