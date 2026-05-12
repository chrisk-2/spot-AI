#!/usr/bin/env bash
set -Eeuo pipefail

REPO="${REPO:-/home/ogre/spot-stack}"
SPOT_BASE_URL="${SPOT_BASE_URL:-http://127.0.0.1:8787}"
MCP_LOCAL_URL="${MCP_LOCAL_URL:-http://127.0.0.1:8001/health}"
BACKUP_ROOT="${BACKUP_ROOT:-/mnt/collective/backups}"
BACKUP_MAX_AGE_HOURS="${BACKUP_MAX_AGE_HOURS:-8}"
VALIDATION_STAMP_FILE="${VALIDATION_STAMP_FILE:-${REPO}/watch/state/operator-validation.json}"
VALIDATION_MAX_AGE_MINUTES="${VALIDATION_MAX_AGE_MINUTES:-1440}"
SELF_HEAL_SCRIPT="${SELF_HEAL_SCRIPT:-${REPO}/watch/spot-self-heal.sh}"

need_cmd(){ command -v "$1" >/dev/null 2>&1 || { echo "ERROR: missing command: $1" >&2; exit 2; }; }

json_bool(){ [[ "${1:-}" == "1" ]] && printf true || printf false; }

http_json_or_empty(){
  local url="$1"
  curl -fsS --connect-timeout 3 --max-time 10 "$url" 2>/dev/null || printf '{}'
}

http_ok(){
  local url="$1"
  curl -fsS --connect-timeout 3 --max-time 10 "$url" >/dev/null 2>&1
}

backup_item(){
  local worker="$1"
  local base="${BACKUP_ROOT}/${worker}/worker-config"
  local p="${base}/latest/metadata.json"
  local snap=""
  local now age_h ts ok="false"

  if [[ ! -f "$p" ]]; then
    snap="$(find "$base" -mindepth 1 -maxdepth 1 -type d -printf '%f\n' 2>/dev/null | grep -E '^[0-9]{8}T[0-9]{6}Z$' | sort | tail -n 1 || true)"
    [[ -n "$snap" ]] && p="${base}/${snap}/metadata.json"
  fi

  now="$(date -u +%s)"
  if [[ -f "$p" ]]; then
    ts="$(jq -r '.timestamp_utc // empty' "$p" 2>/dev/null || true)"
    if [[ "$ts" =~ ^[0-9]{8}T[0-9]{6}Z$ ]]; then
      local epoch
      epoch="$(date -u -d "${ts:0:4}-${ts:4:2}-${ts:6:2} ${ts:9:2}:${ts:11:2}:${ts:13:2}" +%s 2>/dev/null || echo 0)"
      if [[ "$epoch" =~ ^[0-9]+$ && "$epoch" -gt 0 ]]; then
        age_h=$(( (now - epoch) / 3600 ))
        [[ "$age_h" -le "$BACKUP_MAX_AGE_HOURS" ]] && ok="true"
      else
        age_h=null
      fi
    else
      age_h=null
    fi
  else
    ts=""
    age_h=null
  fi

  jq -n \
    --arg worker "$worker" \
    --arg path "$p" \
    --arg timestamp "$ts" \
    --argjson age_hours "$age_h" \
    --argjson ok "$ok" \
    '{worker:$worker,path:$path,timestamp_utc:$timestamp,age_hours:$age_hours,ok:$ok}'
}

main(){
  need_cmd curl
  need_cmd jq
  need_cmd git

  cd "$REPO"

  local generated_at commit dirty health_json routing_json mcp_ok
  generated_at="$(date -u +'%Y-%m-%dT%H:%M:%SZ')"
  commit="$(git log -1 --format='%h %s' 2>/dev/null || echo unknown)"
  if [[ -n "$(git status --short 2>/dev/null)" ]]; then dirty=true; else dirty=false; fi

  health_json="$(http_json_or_empty "${SPOT_BASE_URL}/health")"
  routing_json="$(http_json_or_empty "${SPOT_BASE_URL}/stats/routing-audit")"
  if http_ok "$MCP_LOCAL_URL"; then mcp_ok=true; else mcp_ok=false; fi

  local backups_tmp="" validation_tmp="" self_heal_tmp=""
  backups_tmp="$(mktemp)"
  validation_tmp="$(mktemp)"
  self_heal_tmp="$(mktemp)"
  trap '[[ -n "${backups_tmp:-}" ]] && rm -f "$backups_tmp"; [[ -n "${validation_tmp:-}" ]] && rm -f "$validation_tmp"; [[ -n "${self_heal_tmp:-}" ]] && rm -f "$self_heal_tmp"' EXIT

  jq -s '.' \
    <(backup_item spot-worker-01) \
    <(backup_item spot-worker-02) \
    <(backup_item spot-worker-03) \
    <(backup_item spot-worker-04) \
    > "$backups_tmp"

  if [[ -f "$VALIDATION_STAMP_FILE" ]]; then
    jq --argjson max_age_minutes "$VALIDATION_MAX_AGE_MINUTES" '
      . as $v |
      ((now | floor) - ((.finished_at | fromdateiso8601?) // 0)) as $age_sec |
      . + {
        age_minutes: (($age_sec / 60) | floor),
        max_age_minutes: $max_age_minutes,
        fresh: ((.status == "PASS") and ($age_sec >= 0) and ($age_sec <= ($max_age_minutes * 60)))
      }
    ' "$VALIDATION_STAMP_FILE" > "$validation_tmp"
  else
    jq -n --argjson max_age_minutes "$VALIDATION_MAX_AGE_MINUTES" '{
      status: "UNKNOWN",
      fresh: false,
      age_minutes: null,
      max_age_minutes: $max_age_minutes
    }' > "$validation_tmp"
  fi

  if [[ -x "$SELF_HEAL_SCRIPT" || -f "$SELF_HEAL_SCRIPT" ]]; then
    bash "$SELF_HEAL_SCRIPT" audit > "$self_heal_tmp" 2>/dev/null || jq -n '{ok:false,error:"self_heal_audit_failed"}' > "$self_heal_tmp"
  else
    jq -n --arg path "$SELF_HEAL_SCRIPT" '{ok:false,error:"self_heal_script_missing",path:$path}' > "$self_heal_tmp"
  fi

  jq -n \
    --arg generated_at "$generated_at" \
    --arg commit "$commit" \
    --argjson dirty "$dirty" \
    --argjson health "$health_json" \
    --argjson routing "$routing_json" \
    --argjson mcp_ok "$mcp_ok" \
    --argjson backup_max_age_hours "$BACKUP_MAX_AGE_HOURS" \
    --slurpfile backups "$backups_tmp" \
    --slurpfile validation "$validation_tmp" \
    --slurpfile self_heal "$self_heal_tmp" ' 
      ($backups[0] // []) as $b |
      ($validation[0] // {status:"UNKNOWN", fresh:false}) as $v |
      ($self_heal[0] // {ok:false,error:"self_heal_unavailable"}) as $sh |
      {
        generated_at: $generated_at,
        git: {
          commit: $commit,
          dirty: $dirty
        },
        health: {
          spot_core: (($health.ok // false) == true),
          mcp_local: $mcp_ok,
          uptime_sec: ($health.uptime_sec // null)
        },
        routing: {
          window_count: ($routing.window_count // 0),
          primaries: ($routing.primaries // 0),
          fallbacks: ($routing.fallbacks // 0),
          violations: ($routing.violations // 0),
          manual_overrides: ($routing.manual_overrides // 0),
          ok: ((($routing.ok // false) == true) and (($routing.violations // 0) == 0))
        },
        backups: {
          max_age_hours: $backup_max_age_hours,
          workers_ok: ([$b[] | select(.ok != true)] | length == 0),
          items: $b
        },
        validation: {
          status: ($v.status // "UNKNOWN"),
          fresh: (($v.fresh // false) == true),
          command: ($v.command // null),
          exit_code: ($v.exit_code // null),
          finished_at: ($v.finished_at // null),
          age_minutes: ($v.age_minutes // null),
          max_age_minutes: ($v.max_age_minutes // null),
          duration_sec: ($v.duration_sec // null),
          log_file: ($v.log_file // null)
        },
        self_heal: {
          ok: (($sh.ok // false) == true),
          generated_at: ($sh.generated_at // null),
          mode: ($sh.mode // "audit"),
          autonomy_level: ($sh.policy.autonomy_level // null),
          apply_enabled: (($sh.policy.apply_enabled // false) == true),
          apply_allowlist: ($sh.policy.apply_allowlist // []),
          gated_not_allowlisted: ($sh.policy.gated_not_allowlisted // []),
          action_count: (($sh.actions // []) | length),
          actions: (($sh.actions // []) | map({
            id,
            severity,
            safe_apply,
            reason,
            cooldown: (.cooldown // null)
          })),
          checks: {
            spot_core_ok: (($sh.checks.spot_core.ok // false) == true),
            mcp_local_ok: (($sh.checks.mcp_local.ok // false) == true),
            dashboard_ok: (($sh.checks.dashboard.ok // false) == true),
            routing_ok: (($sh.checks.routing.ok // false) == true),
            backups_ok: (($sh.checks.readiness.backups_ok // false) == true),
            validation_fresh: (($sh.checks.readiness.validation_fresh // false) == true)
          }
        }
      }
      | .status =
        if (.health.spot_core and .health.mcp_local and .routing.ok and .backups.workers_ok and .validation.fresh and (.git.dirty | not))
        then "OK"
        elif (.health.spot_core and .routing.ok and .backups.workers_ok and (.validation.status != "FAIL"))
        then "WARN"
        else "FAIL"
        end
    '
}

main "$@"
