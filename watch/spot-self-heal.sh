#!/usr/bin/env bash
set -Eeuo pipefail

REPO="${REPO:-/home/ogre/spot-stack}"
SPOT_BASE_URL="${SPOT_BASE_URL:-http://127.0.0.1:8787}"
MCP_LOCAL_URL="${MCP_LOCAL_URL:-http://127.0.0.1:8001/health}"
SPOT_UI_OUT_DIR="${SPOT_UI_OUT_DIR:-/var/www/html/spot}"
READINESS_FILE="${READINESS_FILE:-${SPOT_UI_OUT_DIR}/operator-readiness.json}"
META_FILE="${META_FILE:-${SPOT_UI_OUT_DIR}/meta.json}"
DASHBOARD_MAX_AGE_SECONDS="${DASHBOARD_MAX_AGE_SECONDS:-180}"
SELF_HEAL_STATE_FILE="${SELF_HEAL_STATE_FILE:-${REPO}/watch/state/self-heal-state.json}"
SELF_HEAL_COOLDOWN_SECONDS="${SELF_HEAL_COOLDOWN_SECONDS:-300}"
SELF_HEAL_LOG_FILE="${SELF_HEAL_LOG_FILE:-/mnt/collective/logs/spot/self-heal-actions.jsonl}"
SELF_HEAL_MODE="${1:-audit}"

need_cmd(){ command -v "$1" >/dev/null 2>&1 || { echo "ERROR: missing command: $1" >&2; exit 2; }; }

http_json_or_empty(){
  local url="$1"
  curl -fsS --connect-timeout 3 --max-time 10 "$url" 2>/dev/null || printf '{}'
}

http_ok(){
  local url="$1"
  curl -fsS --connect-timeout 3 --max-time 10 "$url" >/dev/null 2>&1
}

json_file_or_empty(){
  local path="$1"
  if [[ -f "$path" ]] && jq -e . "$path" >/dev/null 2>&1; then
    cat "$path"
  else
    printf '{}'
  fi
}

json_or_empty(){
  local raw="${1:-}"
  if jq -e . >/dev/null 2>&1 <<<"$raw"; then
    printf '%s' "$raw"
  else
    printf '{}'
  fi
}

log_event(){
  local event="$1"
  local payload="${2:-{}}"
  if ! jq -e . >/dev/null 2>&1 <<<"$payload"; then
    payload='{}'
  fi
  mkdir -p "$(dirname "$SELF_HEAL_LOG_FILE")"
  jq -nc \
    --arg ts "$(date -u +'%Y-%m-%dT%H:%M:%SZ')" \
    --arg event "$event" \
    --argjson payload "$payload" \
    '{ts:$ts,event:$event,payload:$payload}' >> "$SELF_HEAL_LOG_FILE"
}

log_event_file(){
  local event="$1"
  local payload_file="$2"
  if [[ ! -f "$payload_file" ]] || ! jq -e . "$payload_file" >/dev/null 2>&1; then
    payload_file="/dev/null"
  fi
  mkdir -p "$(dirname "$SELF_HEAL_LOG_FILE")"
  jq -nc \
    --arg ts "$(date -u +'%Y-%m-%dT%H:%M:%SZ')" \
    --arg event "$event" \
    --slurpfile payload "$payload_file" \
    '{ts:$ts,event:$event,payload:($payload[0] // {})}' >> "$SELF_HEAL_LOG_FILE"
}

verify_action_result(){
  local action_id="$1"

  case "$action_id" in
    republish_dashboard)
      local meta_json published_at age
      meta_json="$(json_or_empty "$(json_file_or_empty "$META_FILE")")"
      published_at="$(jq -r '.published_at // empty' <<<"$meta_json")"
      age="$(jq -nr --arg ts "$published_at" 'if ($ts == "") then 999999 else ((now|floor) - (($ts|fromdateiso8601?) // 0)) end')"

      if [[ "$age" -ge 0 && "$age" -le "$DASHBOARD_MAX_AGE_SECONDS" ]]; then
        jq -n --arg id "$action_id" --argjson verify_ok true --argjson age_seconds "$age" \
          '{id:$id,verify_ok:$verify_ok,age_seconds:$age_seconds}'
        return 0
      fi

      jq -n --arg id "$action_id" --argjson verify_ok false --argjson age_seconds "$age" \
        '{id:$id,verify_ok:$verify_ok,age_seconds:$age_seconds,reason:"dashboard meta still stale after republish"}'
      return 1
      ;;
    *)
      jq -n --arg id "$action_id" '{id:$id,verify_ok:false,reason:"no verifier implemented"}'
      return 1
      ;;
  esac
}

main(){
  case "$SELF_HEAL_MODE" in
    audit|plan|dry-run|apply) ;;
    *)
      echo "Usage: $(basename "$0") [audit|plan|dry-run|apply]" >&2
      exit 2
      ;;
  esac

  need_cmd curl
  need_cmd jq
  need_cmd git

  cd "$REPO"

  local generated_at core_json routing_json readiness_json meta_json state_json mcp_ok dirty output_tmp
  generated_at="$(date -u +'%Y-%m-%dT%H:%M:%SZ')"
  core_json="$(json_or_empty "$(http_json_or_empty "${SPOT_BASE_URL}/health")")"
  routing_json="$(json_or_empty "$(http_json_or_empty "${SPOT_BASE_URL}/stats/routing-audit")")"
  readiness_json="$(json_or_empty "$(json_file_or_empty "$READINESS_FILE")")"
  meta_json="$(json_or_empty "$(json_file_or_empty "$META_FILE")")"
  state_json="$(json_or_empty "$(json_file_or_empty "$SELF_HEAL_STATE_FILE")")"

  if http_ok "$MCP_LOCAL_URL"; then mcp_ok=true; else mcp_ok=false; fi
  if [[ -n "$(git status --short 2>/dev/null)" ]]; then dirty=true; else dirty=false; fi

  output_tmp="$(mktemp)"
  trap '[[ -n "${output_tmp:-}" ]] && rm -f "$output_tmp" "${output_tmp}.preview" "${output_tmp}.noop_payload" "${output_tmp}.start_payload" "${output_tmp}.finish_payload" "${output_tmp}.verify_payload"' EXIT

  jq -n \
    --arg generated_at "$generated_at" \
    --arg mode "$SELF_HEAL_MODE" \
    --arg readiness_file "$READINESS_FILE" \
    --arg meta_file "$META_FILE" \
    --arg state_file "$SELF_HEAL_STATE_FILE" \
    --arg log_file "$SELF_HEAL_LOG_FILE" \
    --argjson core "$core_json" \
    --argjson routing "$routing_json" \
    --argjson readiness "$readiness_json" \
    --argjson meta "$meta_json" \
    --argjson state "$state_json" \
    --argjson mcp_ok "$mcp_ok" \
    --argjson git_dirty "$dirty" \
    --argjson dashboard_max_age_seconds "$DASHBOARD_MAX_AGE_SECONDS" \
    --argjson cooldown_seconds "$SELF_HEAL_COOLDOWN_SECONDS" '
      def age_seconds($ts):
        if ($ts == null) then null
        else ((now | floor) - (($ts | fromdateiso8601?) // 0))
        end;

      def previous_action($id):
        (($state.actions // []) | map(select(.id == $id)) | .[0] // null);

      def cooldown_for($id):
        (previous_action($id)) as $prev |
        if ($prev == null or ($prev.last_seen_at // null) == null) then
          {active:false, previous_age_seconds:null, cooldown_seconds:$cooldown_seconds}
        else
          (age_seconds($prev.last_seen_at)) as $age |
          {
            active: (($age != null) and ($age >= 0) and ($age < $cooldown_seconds)),
            previous_age_seconds: $age,
            cooldown_seconds: $cooldown_seconds
          }
        end;

      (age_seconds($meta.published_at // null)) as $dashboard_age |
      {
        generated_at: $generated_at,
        mode: $mode,
        ok: true,
        policy: {
          autonomy_level: (if $mode == "apply" then "level_1_assisted_allowlisted" else "level_0_1_preview" end),
          apply_enabled: ($mode == "apply"),
          apply_allowlist: ["republish_dashboard"],
          backup_required_for_mutation: true,
          log_file: $log_file
        },
        state: {
          file: $state_file,
          exists: (($state | length) > 0),
          updated_at: ($state.updated_at // null),
          last_ok: ($state.last_ok // null),
          cooldown_seconds: $cooldown_seconds
        },
        checks: {
          spot_core: {
            ok: (($core.ok // false) == true),
            uptime_sec: ($core.uptime_sec // null)
          },
          mcp_local: {
            ok: $mcp_ok
          },
          dashboard: {
            ok: (($dashboard_age != null) and ($dashboard_age >= 0) and ($dashboard_age <= $dashboard_max_age_seconds)),
            published_at: ($meta.published_at // null),
            age_seconds: $dashboard_age,
            max_age_seconds: $dashboard_max_age_seconds,
            meta_file: $meta_file,
            readiness_file: $readiness_file
          },
          readiness: {
            status: ($readiness.status // "UNKNOWN"),
            git_dirty: ($readiness.git.dirty // $git_dirty),
            validation_status: ($readiness.validation.status // "UNKNOWN"),
            validation_fresh: (($readiness.validation.fresh // false) == true),
            backups_ok: (($readiness.backups.workers_ok // false) == true)
          },
          routing: {
            ok: (($routing.ok // false) == true),
            primaries: ($routing.primaries // 0),
            fallbacks: ($routing.fallbacks // 0),
            violations: ($routing.violations // 0),
            manual_overrides: ($routing.manual_overrides // 0)
          }
        }
      }
      | .actions = [
          if (.checks.mcp_local.ok | not) then {
            id: "restart_mcp",
            severity: "WARN",
            safe_apply: true,
            cooldown: cooldown_for("restart_mcp"),
            command: "systemctl --user restart spot-mcp.service",
            reason: "MCP local health endpoint is not responding"
          } else empty end,

          if (.checks.dashboard.ok | not) then {
            id: "republish_dashboard",
            severity: "WARN",
            safe_apply: true,
            cooldown: cooldown_for("republish_dashboard"),
            command: "SPOT_UI_ONCE=1 bash watch/spot-ui-publish.sh --once",
            reason: "Published dashboard metadata is missing or stale"
          } else empty end,

          if (.checks.readiness.validation_fresh | not) then {
            id: "refresh_validation_stamp",
            severity: "WARN",
            safe_apply: true,
            cooldown: cooldown_for("refresh_validation_stamp"),
            command: "watch/spot-validation-stamp.sh -- spot validate",
            reason: "Validation stamp is missing, stale, or not PASS"
          } else empty end,

          if ((.checks.routing.violations // 0) > 0) then {
            id: "routing_violation_escalate",
            severity: "FAIL",
            safe_apply: false,
            cooldown: cooldown_for("routing_violation_escalate"),
            command: null,
            reason: "Routing violations detected; automatic routing rewrites are forbidden"
          } else empty end,

          if (.checks.readiness.backups_ok | not) then {
            id: "backup_gate_escalate",
            severity: "FAIL",
            safe_apply: false,
            cooldown: cooldown_for("backup_gate_escalate"),
            command: null,
            reason: "Backup freshness gate is not OK; no automatic changes should run"
          } else empty end,

          if (.checks.readiness.git_dirty == true) then {
            id: "repo_dirty_warn",
            severity: "WARN",
            safe_apply: false,
            cooldown: cooldown_for("repo_dirty_warn"),
            command: null,
            reason: "Repository has uncommitted changes"
          } else empty end
        ]
      | .ok =
          (
            (.checks.spot_core.ok == true)
            and (.checks.routing.ok == true)
            and ((.checks.routing.violations // 0) == 0)
            and (.checks.readiness.backups_ok == true)
          )
    ' > "$output_tmp"

  if [[ "$SELF_HEAL_MODE" == "plan" || "$SELF_HEAL_MODE" == "dry-run" || "$SELF_HEAL_MODE" == "apply" ]]; then
    mkdir -p "$(dirname "$SELF_HEAL_STATE_FILE")"
    jq '. as $root | {
      updated_at: $root.generated_at,
      last_mode: $root.mode,
      last_ok: $root.ok,
      last_action_ids: [$root.actions[].id],
      checks: $root.checks,
      actions: ($root.actions | map(. + {last_seen_at: $root.generated_at}))
    }' "$output_tmp" > "$SELF_HEAL_STATE_FILE"
  fi

  if [[ "$SELF_HEAL_MODE" == "dry-run" || "$SELF_HEAL_MODE" == "apply" ]]; then
    jq '. + {
      would_apply: [
        .actions[]
        | select(.safe_apply == true)
        | select((.cooldown.active // false) == false)
      ],
      blocked_or_skipped: [
        .actions[]
        | select((.safe_apply != true) or ((.cooldown.active // false) == true))
      ]
    }' "$output_tmp" > "${output_tmp}.preview"

    if [[ "$SELF_HEAL_MODE" == "apply" ]]; then
      local apply_ids
      apply_ids="$(jq -r '.would_apply[].id' "${output_tmp}.preview")"

      if [[ -z "$apply_ids" ]]; then
        jq '{ok, actions, would_apply, blocked_or_skipped}' "${output_tmp}.preview" > "${output_tmp}.noop_payload"
        log_event_file "apply_noop" "${output_tmp}.noop_payload"
        jq '. + {apply_result:{status:"NOOP", executed:[], skipped_reason:"no eligible safe actions"}}' "${output_tmp}.preview"
        return 0
      fi

      local executed_tmp
      executed_tmp="$(mktemp)"
      printf '[]' > "$executed_tmp"

      while IFS= read -r action_id; do
        [[ -z "$action_id" ]] && continue

        case "$action_id" in
          republish_dashboard)
            local start_ts finish_ts exit_code verify_rc
            jq --arg id "$action_id" '.would_apply[] | select(.id == $id)' "${output_tmp}.preview" > "${output_tmp}.start_payload"
            log_event_file "apply_start" "${output_tmp}.start_payload"
            start_ts="$(date -u +'%Y-%m-%dT%H:%M:%SZ')"

            set +e
            SPOT_UI_ONCE=1 bash watch/spot-ui-publish.sh --once >/tmp/spot-self-heal-republish.log 2>&1
            exit_code=$?
            verify_action_result "$action_id" > "${output_tmp}.verify_payload"
            verify_rc=$?
            set -e

            finish_ts="$(date -u +'%Y-%m-%dT%H:%M:%SZ')"
            jq -n \
              --arg id "$action_id" \
              --arg started_at "$start_ts" \
              --arg finished_at "$finish_ts" \
              --argjson exit_code "$exit_code" \
              --slurpfile verify "${output_tmp}.verify_payload" \
              --rawfile log /tmp/spot-self-heal-republish.log \
              '{id:$id,started_at:$started_at,finished_at:$finished_at,exit_code:$exit_code,verify:($verify[0] // {}),log:$log}' > "${output_tmp}.finish_payload"

            log_event_file "apply_finish" "${output_tmp}.finish_payload"

            jq --slurpfile item "${output_tmp}.finish_payload" '. + [$item[0]]' "$executed_tmp" > "${executed_tmp}.next"
            mv "${executed_tmp}.next" "$executed_tmp"

            if [[ "$exit_code" -ne 0 || "$verify_rc" -ne 0 ]]; then
              jq --slurpfile executed "$executed_tmp" '. + {apply_result:{executed:$executed[0], status:"FAIL"}}' "${output_tmp}.preview"
              rm -f "$executed_tmp"
              return 1
            fi
            ;;
          *)
            log_event "apply_blocked_unknown_action" "$(jq -n --arg id "$action_id" '{id:$id,reason:"action not allowlisted for apply"}')"
            ;;
        esac
      done <<< "$apply_ids"

      jq --slurpfile executed "$executed_tmp" '. + {apply_result:{executed:$executed[0], status:"OK"}}' "${output_tmp}.preview"
      rm -f "$executed_tmp"
    else
      cat "${output_tmp}.preview"
    fi
  else
    cat "$output_tmp"
  fi
}

main "$@"
