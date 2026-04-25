#!/usr/bin/env bash
set -Eeuo pipefail

SPOT_UI_JSON="${SPOT_UI_JSON:-/var/www/html/spot/spot.json}"
SPOT_UI_HISTORY_JSON="${SPOT_UI_HISTORY_JSON:-/var/www/html/spot/history.json}"
REMEDIATION_STATE_FILE="${REMEDIATION_STATE_FILE:-/home/ogre/spot-stack/watch/state/remediation-state.json}"
RISK_JQ_FILE="${RISK_JQ_FILE:-/home/ogre/spot-stack/watch/spot-ui-risk.json.jq}"
STALE_SNAPSHOT_SECONDS="${STALE_SNAPSHOT_SECONDS:-180}"

need_file(){ [[ -f "$1" ]] || { echo "ERROR: missing file: $1" >&2; exit 2; }; }
need_cmd(){ command -v "$1" >/dev/null 2>&1 || { echo "ERROR: missing command: $1" >&2; exit 2; }; }

need_cmd jq
need_file "$SPOT_UI_JSON"
need_file "$RISK_JQ_FILE"

TMPDIR="$(mktemp -d)"
trap 'rm -rf "$TMPDIR"' EXIT

cp "$SPOT_UI_JSON" "$TMPDIR/spot.json"
if [[ -f "$SPOT_UI_HISTORY_JSON" ]]; then cp "$SPOT_UI_HISTORY_JSON" "$TMPDIR/history.json"; else printf '{"count":0,"trends":{}}' > "$TMPDIR/history.json"; fi
if [[ -f "$REMEDIATION_STATE_FILE" ]]; then cp "$REMEDIATION_STATE_FILE" "$TMPDIR/remediation.json"; else printf '{}' > "$TMPDIR/remediation.json"; fi

jq -n \
  --slurpfile sf "$TMPDIR/spot.json" \
  --slurpfile hf "$TMPDIR/history.json" \
  --slurpfile rf "$TMPDIR/remediation.json" \
  --argjson stale "$STALE_SNAPSHOT_SECONDS" \
  '($sf[0]) as $s | ($hf[0]) as $h | ($rf[0]) as $r | def risk_score($s; $h; $r; $stale):
  def lastn($a; $n): ($a // [] | if length > $n then .[(length-$n):] else . end);
  def increasing($a): ($a|length) >= 3 and ($a[-1] > $a[-2]) and ($a[-2] > $a[-3]);
  def age_sec: ((now | floor) - (($h.last_generated_at // $s.generated_at) | fromdateiso8601? // (now|floor)));
  def rem_entries: ($r | to_entries | map(select(.key != "_meta")));
  def worker_fail_count: (($s.workers // []) | map(select(.ok != true)) | length);
  def worker_warn_count: (($s.workers // []) | map(select(.severity == "warn")) | length);
  def quarantine_count: (rem_entries | map(select(.value.quarantined == true)) | length);
  def remediation_violation_count: (rem_entries | map((.value.violation_count_window // 0)) | add // 0);
  def nonok_count: (($h.trends.banner_statuses // []) | lastn(.;5) | map(select(. != "OK")) | length);
  def points:
    0
    + (if ($s.core.ok != true) then 40 else 0 end)
    + (if ($s.banner.status == "ALERT") then 30 elif ($s.banner.status == "WARN") then 12 else 0 end)
    + (if ($s.routing.status == "FAIL") then 30 elif ($s.routing.status == "WARN") then 10 else 0 end)
    + (($s.routing.violations // 0) * 4)
    + (($s.routing.fallbacks // 0) * 2)
    + (worker_fail_count * 20)
    + (worker_warn_count * 8)
    + (quarantine_count * 15)
    + (remediation_violation_count * 3)
    + (if age_sec > $stale then 15 else 0 end)
    + (if increasing($h.trends.routing_fallbacks // []) then 8 else 0 end)
    + (if increasing($h.trends.routing_violations // []) then 12 else 0 end)
    + (if nonok_count >= 3 then 10 else 0 end);
  points as $p
  | {
      score: ([$p,100] | min),
      level: (if $p >= 75 then "CRITICAL" elif $p >= 45 then "HIGH" elif $p >= 20 then "ELEVATED" else "NORMAL" end),
      factors: [
        (if ($s.core.ok != true) then "core health failing" else empty end),
        (if ($s.banner.status != "OK") then "incident banner=" + $s.banner.status else empty end),
        (if ($s.routing.status != "OK") then "routing status=" + $s.routing.status else empty end),
        (if ($s.routing.violations // 0) > 0 then "routing violations=" + (($s.routing.violations // 0)|tostring) else empty end),
        (if ($s.routing.fallbacks // 0) > 0 then "routing fallbacks=" + (($s.routing.fallbacks // 0)|tostring) else empty end),
        (if worker_fail_count > 0 then "worker failures=" + (worker_fail_count|tostring) else empty end),
        (if worker_warn_count > 0 then "worker warnings=" + (worker_warn_count|tostring) else empty end),
        (if quarantine_count > 0 then "active quarantines=" + (quarantine_count|tostring) else empty end),
        (if remediation_violation_count > 0 then "remediation violation memory=" + (remediation_violation_count|tostring) else empty end),
        (if age_sec > $stale then "publisher stale=" + (age_sec|tostring) + "s" else empty end),
        (if increasing($h.trends.routing_fallbacks // []) then "fallbacks rising" else empty end),
        (if increasing($h.trends.routing_violations // []) then "violations rising" else empty end),
        (if nonok_count >= 3 then "persistent non-OK banner" else empty end)
      ]
    };
risk_score($s; $h; $r; $stale)'
