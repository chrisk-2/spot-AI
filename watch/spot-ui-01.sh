#!/usr/bin/env bash
set -Eeuo pipefail

SPOT_BASE_URL="${SPOT_BASE_URL:-http://127.0.0.1:8787}"
FLEET_STATUS_FILE="${FLEET_STATUS_FILE:-/home/ogre/spot-stack/watch/state/fleet-status.json}"
CURL_TIMEOUT="${CURL_TIMEOUT:-15}"
NO_COLOR="${NO_COLOR:-0}"

need_cmd(){ command -v "$1" >/dev/null 2>&1 || { echo "ERROR: missing command $1" >&2; exit 2; }; }
api_get(){ curl -fsS --connect-timeout 5 --max-time "$CURL_TIMEOUT" "${SPOT_BASE_URL}$1"; }

color(){
  [[ "$NO_COLOR" = 1 || ! -t 1 ]] && { printf '%s' "$2"; return; }
  case "$1" in
    green) printf '\033[32m%s\033[0m' "$2" ;;
    yellow) printf '\033[33m%s\033[0m' "$2" ;;
    red) printf '\033[31m%s\033[0m' "$2" ;;
    cyan) printf '\033[36m%s\033[0m' "$2" ;;
    bold) printf '\033[1m%s\033[0m' "$2" ;;
    *) printf '%s' "$2" ;;
  esac
}
status_color(){ case "$1" in OK|true) color green "$1" ;; WARN) color yellow "$1" ;; FAIL|false|ALERT) color red "$1" ;; *) printf '%s' "$1" ;; esac; }
header(){ printf '\n%s\n' "$(color cyan "=== $1 ===")"; }

collect_json(){
  need_cmd jq
  local health ping audit state_ts
  health="$(api_get /health)"
  ping="$(api_get /fleet/ping)"
  audit="$(api_get '/stats/routing-audit?limit=50')"
  state_ts="unknown"
  [[ -f "$FLEET_STATUS_FILE" ]] && state_ts="$(jq -r '.timestamp // "unknown"' "$FLEET_STATUS_FILE")"

  jq -n \
    --arg state_ts "$state_ts" \
    --argjson health "$health" \
    --argjson workers "$ping" \
    --argjson audit "$audit" \
    '($audit | if (.violations//0)>0 then "WARN" elif (.ok==true) then "OK" else "FAIL" end) as $route_state
     | ($workers | to_entries | map({
          worker: .key,
          role: (.value.primary_role // "unknown"),
          ok: (.value.ok // false),
          eligible: (.value.eligible // false),
          quarantined: (.value.quarantined // false),
          degraded: (.value.degraded // false),
          running_jobs: (.value.running_jobs // 0),
          avg_total_ms: (.value.latency.avg_total_ms // null),
          p50_total_ms: (.value.latency.p50_total_ms // null),
          avg_tok_per_sec: (.value.latency.avg_tok_per_sec // null)
        } | .severity = (if (.ok|not) then "fail" elif .quarantined then "warn" elif .degraded then "warn" elif (.eligible|not) then "warn" else "ok" end))) as $worker_list
     | ([
          (if ($health.ok|not) then "core health is failing" else empty end),
          (if $route_state == "FAIL" then "routing audit failed" else empty end),
          (if ($audit.violations//0) > 0 then "routing violations present in audit window" else empty end),
          ($worker_list[] | select(.severity=="fail") | "worker " + .worker + " is failing"),
          ($worker_list[] | select(.quarantined==true) | "worker " + .worker + " is quarantined"),
          ($worker_list[] | select(.degraded==true) | "worker " + .worker + " is degraded")
        ]) as $incidents
     | {
        generated_at: (now | todateiso8601),
        spot_base_url: env.SPOT_BASE_URL,
        state_timestamp: $state_ts,
        banner: {
          status: (if ($incidents|length)==0 then "OK" elif ($incidents|map(test("failing|failed"))|any) then "ALERT" else "WARN" end),
          incidents: $incidents
        },
        core: {ok: $health.ok, uptime_sec: $health.uptime_sec},
        routing: {
          status: $route_state,
          ok: $audit.ok,
          window_count: ($audit.window_count // 0),
          primaries: ($audit.primaries // 0),
          fallbacks: ($audit.fallbacks // 0),
          violations: ($audit.violations // 0),
          manual_overrides: ($audit.manual_overrides // 0),
          last_violation_ts: ($audit.last_violation_ts // null)
        },
        workers: $worker_list
      }'
}

cmd_json(){ collect_json | jq .; }

cmd_cockpit(){
  local data core_state route_state banner
  data="$(collect_json)"
  core_state="$(jq -r 'if .core.ok then "OK" else "FAIL" end' <<<"$data")"
  route_state="$(jq -r '.routing.status' <<<"$data")"
  banner="$(jq -r '.banner.status' <<<"$data")"

  header "SPOT UI 01 COCKPIT"
  printf 'Banner:    %s\n' "$(status_color "$banner")"
  jq -r '.banner.incidents[]? | "  - " + .' <<<"$data"
  printf 'Core:      %s  uptime=%ss\n' "$(status_color "$core_state")" "$(jq -r '.core.uptime_sec' <<<"$data")"
  printf 'State:     %s\n' "$(jq -r '.state_timestamp' <<<"$data")"
  printf 'Routing:   %s  primary=%s fallback=%s violations=%s manual=%s window=%s\n' \
    "$(status_color "$route_state")" \
    "$(jq -r '.routing.primaries' <<<"$data")" \
    "$(jq -r '.routing.fallbacks' <<<"$data")" \
    "$(jq -r '.routing.violations' <<<"$data")" \
    "$(jq -r '.routing.manual_overrides' <<<"$data")" \
    "$(jq -r '.routing.window_count' <<<"$data")"
  printf 'Last viol: %s\n' "$(jq -r '.routing.last_violation_ts // "none"' <<<"$data")"

  header "WORKERS"
  jq -r '.workers[] | @base64' <<<"$data" | while read -r row; do
    w(){ printf '%s' "$row" | base64 -d | jq -r "$1"; }
    local ok st sev
    ok="$(w '.ok')"
    sev="$(w '.severity')"
    [[ "$ok" = true ]] && st=OK || st=FAIL
    printf '  %-15s [%-7s] %s/%s  eligible=%-5s quarantine=%-5s degraded=%-5s jobs=%s avg_ms=%s tok_s=%s\n' \
      "$(w '.worker')" "$(w '.role')" "$(status_color "$st")" "$(status_color "$sev")" \
      "$(w '.eligible')" "$(w '.quarantined')" "$(w '.degraded')" \
      "$(w '.running_jobs')" "$(w '.avg_total_ms // "n/a"')" "$(w '.avg_tok_per_sec // "n/a"')"
  done

  header "OPERATOR"
  echo "  legacy ops:   spot-ops.sh status"
  echo "  validation:   spot-ops.sh validate"
  echo "  audit:        spot-ops.sh audit 50"
  echo "  quarantine:   spot-ops.sh quarantine-state"
  echo "  logs:         spot-ops.sh logs both 100"
}

html_escape(){ sed -e 's/&/\&amp;/g' -e 's/</\&lt;/g' -e 's/>/\&gt;/g'; }

cmd_html(){
  local data rows status_class banner_class incidents
  data="$(collect_json)"
  rows="$(jq -r '.workers[] | "<tr class=\"" + .severity + "\"><td>" + .worker + "</td><td>" + .role + "</td><td>" + (if .ok then "OK" else "FAIL" end) + "</td><td>" + .severity + "</td><td>" + (.eligible|tostring) + "</td><td>" + (.quarantined|tostring) + "</td><td>" + (.degraded|tostring) + "</td><td>" + (.running_jobs|tostring) + "</td><td>" + ((.avg_total_ms//"n/a")|tostring) + "</td><td>" + ((.avg_tok_per_sec//"n/a")|tostring) + "</td></tr>"' <<<"$data")"
  status_class="$(jq -r '.routing.status | ascii_downcase' <<<"$data")"
  banner_class="$(jq -r '.banner.status | ascii_downcase' <<<"$data")"
  incidents="$(jq -r 'if (.banner.incidents|length)==0 then "<li>No active incidents</li>" else (.banner.incidents[] | "<li>" + . + "</li>") end' <<<"$data")"
  cat <<HTML
<!doctype html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="refresh" content="60">
<title>Spot UI 01 Cockpit</title>
<style>
body{font-family:system-ui,Segoe UI,sans-serif;background:#0b1020;color:#e6edf3;margin:2rem}.card{background:#111827;border:1px solid #263244;border-radius:12px;padding:1rem;margin:1rem 0}.banner{border-radius:12px;padding:1rem;margin:1rem 0;border:1px solid #263244}.banner.ok{background:#0f2a1d}.banner.warn{background:#3a2f12}.banner.alert{background:#3b1517}table{border-collapse:collapse;width:100%}th,td{border-bottom:1px solid #263244;padding:.5rem;text-align:left}.ok{color:#7ee787}.warn{color:#f2cc60}.fail,.alert{color:#ff7b72}.meta{color:#9ca3af}tr.warn{background:#241f11}tr.fail{background:#2a1114}code{color:#9cdcfe}
</style></head><body>
<h1>Spot UI 01 Cockpit</h1>
<div class="banner $banner_class"><h2>Incident Banner: <span class="$banner_class">$(jq -r '.banner.status' <<<"$data")</span></h2><ul>$incidents</ul></div>
<div class="card"><h2>Core</h2><p>Status: <b class="$(jq -r 'if .core.ok then "ok" else "fail" end' <<<"$data")">$(jq -r 'if .core.ok then "OK" else "FAIL" end' <<<"$data")</b></p><p>Uptime: $(jq -r '.core.uptime_sec' <<<"$data")s</p><p class="meta">State: $(jq -r '.state_timestamp' <<<"$data" | html_escape)</p></div>
<div class="card"><h2>Routing</h2><p>Status: <b class="$status_class">$(jq -r '.routing.status' <<<"$data")</b></p><p>Primary $(jq -r '.routing.primaries' <<<"$data") · Fallback $(jq -r '.routing.fallbacks' <<<"$data") · Violations $(jq -r '.routing.violations' <<<"$data") · Manual $(jq -r '.routing.manual_overrides' <<<"$data") · Window $(jq -r '.routing.window_count' <<<"$data")</p><p class="meta">Last violation: $(jq -r '.routing.last_violation_ts // "none"' <<<"$data")</p></div>
<div class="card"><h2>Workers</h2><table><thead><tr><th>Worker</th><th>Role</th><th>Status</th><th>Severity</th><th>Eligible</th><th>Quarantine</th><th>Degraded</th><th>Jobs</th><th>Avg ms</th><th>Tok/s</th></tr></thead><tbody>$rows</tbody></table></div>
<p class="meta">Generated: $(jq -r '.generated_at' <<<"$data") · JSON feed: <code>spot.json</code></p>
</body></html>
HTML
}

usage(){ echo "Usage: $(basename "$0") [cockpit|--json|json|--html|html]"; }

case "${1:-cockpit}" in
  cockpit) cmd_cockpit ;;
  --json|json) cmd_json ;;
  --html|html) cmd_html ;;
  -h|--help|help) usage ;;
  *) usage; exit 2 ;;
esac
