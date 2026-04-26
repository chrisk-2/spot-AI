#!/usr/bin/env bash
set -Eeuo pipefail

SPOT_UI_RISK_RENDERER="${SPOT_UI_RISK_RENDERER:-/home/ogre/spot-stack/watch/spot-ui-render-risk.sh}"
SPOT_UI_REMEDIATION_MAP="${SPOT_UI_REMEDIATION_MAP:-/home/ogre/spot-stack/watch/spot-ui-remediation-map.sh}"
SPOT_UI_STATE_DIR="${SPOT_UI_STATE_DIR:-/home/ogre/spot-stack/watch/state}"
SPOT_UI_LEDGER_FILE="${SPOT_UI_LEDGER_FILE:-${SPOT_UI_STATE_DIR}/spot-ui-incidents.jsonl}"
SPOT_UI_ENGINE_STATE_FILE="${SPOT_UI_ENGINE_STATE_FILE:-${SPOT_UI_STATE_DIR}/incident-engine-state.json}"
SPOT_UI_LEDGER_LIMIT="${SPOT_UI_LEDGER_LIMIT:-200}"
WARN_PROMOTE_COUNT="${WARN_PROMOTE_COUNT:-3}"
HIGH_PROMOTE_COUNT="${HIGH_PROMOTE_COUNT:-2}"
FACTOR_PROMOTE_COUNT="${FACTOR_PROMOTE_COUNT:-3}"

need_file(){ [[ -f "$1" ]] || { echo "ERROR: missing file: $1" >&2; exit 2; }; }
need_cmd(){ command -v "$1" >/dev/null 2>&1 || { echo "ERROR: missing command: $1" >&2; exit 2; }; }

init_state(){
  mkdir -p "$SPOT_UI_STATE_DIR"
  if [[ ! -f "$SPOT_UI_ENGINE_STATE_FILE" ]]; then
    jq -n '{version:1,last_level:"NONE",level_streak:0,factor_counts:{},open_signatures:{},last_incident_id:0,last_capture_ts:null}' > "$SPOT_UI_ENGINE_STATE_FILE"
  fi
}

trim(){
  [[ -f "$SPOT_UI_LEDGER_FILE" ]] || return 0
  local tmp="${SPOT_UI_LEDGER_FILE}.$$"
  tail -n "$SPOT_UI_LEDGER_LIMIT" "$SPOT_UI_LEDGER_FILE" > "$tmp"
  mv "$tmp" "$SPOT_UI_LEDGER_FILE"
}

fallback_remediation(){
  jq -c -n --argjson factors "$1" '{class:"general_investigation",suggestion:"Review incident factors, current fleet status, routing audit, and recent decisions.",risk_class:"LOW",backup_required:false,autonomy:"advisory_only",state:"advisory",policy_note:"advisory only; future mutating paths must use Spot Core backup-first policy",factors:$factors}'
}

capture(){
  need_file "$SPOT_UI_RISK_RENDERER"
  need_cmd jq
  init_state

  local ts risk state result new_state incident factors remediation
  ts="$(date -u +'%Y-%m-%dT%H:%M:%SZ')"
  risk="$(bash "$SPOT_UI_RISK_RENDERER")"
  state="$(cat "$SPOT_UI_ENGINE_STATE_FILE")"

  result="$(jq -c -n \
    --arg ts "$ts" \
    --argjson risk "$risk" \
    --argjson state "$state" \
    --argjson warn_count "$WARN_PROMOTE_COUNT" \
    --argjson high_count "$HIGH_PROMOTE_COUNT" \
    --argjson factor_count "$FACTOR_PROMOTE_COUNT" '
    def norm_level($x): ($x // "UNKNOWN" | tostring | ascii_upcase);
    def sev_for($level; $streak):
      if $level == "CRITICAL" then "HIGH"
      elif $level == "HIGH" and $streak >= $high_count then "WARN"
      elif $level == "ELEVATED" and $streak >= $warn_count then "INFO"
      elif $level == "WARN" and $streak >= $warn_count then "INFO"
      else null end;
    def factor_key($f): ($f|tostring|gsub("[^A-Za-z0-9_.:-]";"_"));
    def sig($severity; $trigger; $factors): ($severity+":"+$trigger+":"+(($factors // [])|join("|")));
    ($risk.level | norm_level(.)) as $level |
    (($risk.factors // []) | map(tostring)) as $factors |
    (($state.last_level // "NONE") | norm_level(.)) as $prev_level |
    (if $level == $prev_level then (($state.level_streak // 0) + 1) else 1 end) as $level_streak |
    (reduce $factors[] as $f (($state.factor_counts // {}); .[factor_key($f)] = ((.[factor_key($f)] // 0) + 1))) as $factor_counts |
    ($factors | map(select(($factor_counts[factor_key(.)] // 0) >= $factor_count))) as $persistent_factors |
    (sev_for($level; $level_streak)) as $level_sev |
    (if ($persistent_factors|length) > 0 then "WARN" else null end) as $factor_sev |
    (if $level_sev != null then $level_sev elif $factor_sev != null then $factor_sev else null end) as $severity |
    (if $level_sev != null then "risk_level_streak" elif $factor_sev != null then "persistent_factor" else null end) as $trigger |
    (if $trigger == "persistent_factor" then $persistent_factors else $factors end) as $incident_factors |
    (if $severity != null then sig($severity; $trigger; $incident_factors) else null end) as $signature |
    (if $signature != null then (($state.open_signatures // {})[$signature] // null) else null end) as $existing |
    (if $severity != null and $existing == null then (($state.last_incident_id // 0) + 1) else ($state.last_incident_id // 0) end) as $last_id |
    (if $severity != null and $existing == null then ("INC-" + ($last_id|tostring)) else null end) as $incident_id |
    (($state.open_signatures // {}) + (if $incident_id != null then {($signature): $incident_id} else {} end)) as $open_signatures |
    {
      incident: (if $incident_id == null then null else {
        ts:$ts,type:"incident_opened",incident_id:$incident_id,severity:$severity,trigger:$trigger,signature:$signature,ack_state:"open",remediation_state:"pending",risk:$risk,factors:$incident_factors,engine:{level:$level,level_streak:$level_streak,persistent_factors:$persistent_factors}
      } end),
      state: {version:1,last_level:$level,level_streak:$level_streak,factor_counts:$factor_counts,open_signatures:$open_signatures,last_incident_id:$last_id,last_capture_ts:$ts,last_risk:$risk}
    }' )"

  new_state="$(jq -c '.state' <<<"$result")"
  printf '%s\n' "$new_state" > "$SPOT_UI_ENGINE_STATE_FILE"

  incident="$(jq -c '.incident // empty' <<<"$result")"
  if [[ -n "$incident" ]]; then
    factors="$(jq -c '.factors // []' <<<"$incident")"
    if [[ -x "$SPOT_UI_REMEDIATION_MAP" ]]; then
      remediation="$(bash "$SPOT_UI_REMEDIATION_MAP" "$factors" || fallback_remediation "$factors")"
    else
      remediation="$(fallback_remediation "$factors")"
    fi
    incident="$(jq -c --argjson remediation "$remediation" '. + {remediation:$remediation}' <<<"$incident")"
    printf '%s\n' "$incident" >> "$SPOT_UI_LEDGER_FILE"
  fi
  trim
}

summary(){
  need_cmd jq
  local state='{}'
  [[ -f "$SPOT_UI_ENGINE_STATE_FILE" ]] && state="$(cat "$SPOT_UI_ENGINE_STATE_FILE")"
  if [[ ! -f "$SPOT_UI_LEDGER_FILE" ]]; then
    jq -n --argjson state "$state" '{count:0,latest:null,transitions:[],open_incidents:[],engine_state:$state,items:[]}'
    return 0
  fi
  tail -n "$SPOT_UI_LEDGER_LIMIT" "$SPOT_UI_LEDGER_FILE" | jq -s --argjson state "$state" '{count:length,latest:.[-1],transitions:[.[]|select(.type=="risk_transition")],open_incidents:[.[]|select(.type=="incident_opened" and (.ack_state // "open") == "open")],engine_state:$state,items:.}'
}

case "${1:-capture}" in
  capture) capture ;;
  summary|--summary) summary ;;
  trim) trim ;;
  -h|--help|help) echo "Usage: $(basename "$0") [capture|summary|trim]" ;;
  *) echo "ERROR: unknown command: $1" >&2; exit 2 ;;
esac
