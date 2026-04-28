#!/usr/bin/env bash
set -Eeuo pipefail

REPO="${REPO:-/home/ogre/spot-stack}"
SPOT_BASE_URL="${SPOT_BASE_URL:-http://127.0.0.1:8787}"
MCP_LOCAL_URL="${MCP_LOCAL_URL:-http://127.0.0.1:8001/health}"
SPOT_UI_OUT_DIR="${SPOT_UI_OUT_DIR:-/var/www/html/spot}"
READINESS_FILE="${READINESS_FILE:-${SPOT_UI_OUT_DIR}/operator-readiness.json}"
META_FILE="${META_FILE:-${SPOT_UI_OUT_DIR}/meta.json}"
DASHBOARD_MAX_AGE_SECONDS="${DASHBOARD_MAX_AGE_SECONDS:-180}"
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
  if [[ -f "$path" ]]; then
    cat "$path"
  else
    printf '{}'
  fi
}

main(){
  case "$SELF_HEAL_MODE" in
    audit|plan) ;;
    apply)
      echo "ERROR: apply mode is intentionally not implemented in Self-Heal v1" >&2
      exit 2
      ;;
    *)
      echo "Usage: $(basename "$0") [audit|plan]" >&2
      exit 2
      ;;
  esac

  need_cmd curl
  need_cmd jq
  need_cmd git

  cd "$REPO"

  local generated_at core_json routing_json readiness_json meta_json mcp_ok dirty
  generated_at="$(date -u +'%Y-%m-%dT%H:%M:%SZ')"
  core_json="$(http_json_or_empty "${SPOT_BASE_URL}/health")"
  routing_json="$(http_json_or_empty "${SPOT_BASE_URL}/stats/routing-audit")"
  readiness_json="$(json_file_or_empty "$READINESS_FILE")"
  meta_json="$(json_file_or_empty "$META_FILE")"

  if http_ok "$MCP_LOCAL_URL"; then mcp_ok=true; else mcp_ok=false; fi
  if [[ -n "$(git status --short 2>/dev/null)" ]]; then dirty=true; else dirty=false; fi

  jq -n \
    --arg generated_at "$generated_at" \
    --arg mode "$SELF_HEAL_MODE" \
    --arg readiness_file "$READINESS_FILE" \
    --arg meta_file "$META_FILE" \
    --argjson core "$core_json" \
    --argjson routing "$routing_json" \
    --argjson readiness "$readiness_json" \
    --argjson meta "$meta_json" \
    --argjson mcp_ok "$mcp_ok" \
    --argjson git_dirty "$dirty" \
    --argjson dashboard_max_age_seconds "$DASHBOARD_MAX_AGE_SECONDS" '
      def age_seconds($ts):
        if ($ts == null) then null
        else ((now | floor) - (($ts | fromdateiso8601?) // 0))
        end;

      (age_seconds($meta.published_at // null)) as $dashboard_age |
      {
        generated_at: $generated_at,
        mode: $mode,
        ok: true,
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
            command: "systemctl --user restart spot-mcp.service",
            reason: "MCP local health endpoint is not responding"
          } else empty end,

          if (.checks.dashboard.ok | not) then {
            id: "republish_dashboard",
            severity: "WARN",
            safe_apply: true,
            command: "SPOT_UI_ONCE=1 bash watch/spot-ui-publish.sh --once",
            reason: "Published dashboard metadata is missing or stale"
          } else empty end,

          if (.checks.readiness.validation_fresh | not) then {
            id: "refresh_validation_stamp",
            severity: "WARN",
            safe_apply: true,
            command: "watch/spot-validation-stamp.sh -- spot validate",
            reason: "Validation stamp is missing, stale, or not PASS"
          } else empty end,

          if ((.checks.routing.violations // 0) > 0) then {
            id: "routing_violation_escalate",
            severity: "FAIL",
            safe_apply: false,
            command: null,
            reason: "Routing violations detected; automatic routing rewrites are forbidden"
          } else empty end,

          if (.checks.readiness.backups_ok | not) then {
            id: "backup_gate_escalate",
            severity: "FAIL",
            safe_apply: false,
            command: null,
            reason: "Backup freshness gate is not OK; no automatic changes should run"
          } else empty end,

          if (.checks.readiness.git_dirty == true) then {
            id: "repo_dirty_warn",
            severity: "WARN",
            safe_apply: false,
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
    '
}

main "$@"
