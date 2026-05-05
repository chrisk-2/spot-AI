#!/usr/bin/env bash
set -Eeuo pipefail

BASE_DIR="${BASE_DIR:-/home/ogre/spot-stack/watch}"
PREFLIGHT_DIR="${PREFLIGHT_DIR:-${BASE_DIR}/executor-preflights}"
STATE_DIR="${STATE_DIR:-${BASE_DIR}/state}"
SUMMARY_FILE="${SUMMARY_FILE:-${STATE_DIR}/executor-preflight-summary.json}"
POLICY_FILE="${POLICY_FILE:-${BASE_DIR}/policy/action-policy.json}"
REGISTRY_FILE="${REGISTRY_FILE:-${BASE_DIR}/policy/plugin-registry.json}"

usage() {
  cat <<'USAGE'
Usage:
  spot-executor-preflight.sh create <plugin-request-id-or-file>
  spot-executor-preflight.sh verify <preflight-id-or-file>
  spot-executor-preflight.sh show <preflight-id-or-file>
  spot-executor-preflight.sh list [count]
  spot-executor-preflight.sh summary

Phase 2.14 only:
- produces executor preflight artifacts
- verifies plugin request, plugin registry, and action policy
- keeps execution and mutation blocked
- performs no service restart, config write, network mutation, backup binding, or executor dispatch
USAGE
}

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "ERROR: required command not found: $1" >&2
    exit 2
  }
}

stamp() { date -u +%Y%m%d-%H%M%S; }

json_get() {
  local file="$1" expr="$2"
  python3 - "$file" "$expr" <<'PY'
import json, sys
from pathlib import Path

path = Path(sys.argv[1])
expr = sys.argv[2]
data = json.loads(path.read_text())

cur = data
for part in expr.split("."):
    if part == "":
        continue
    if isinstance(cur, dict) and part in cur:
        cur = cur[part]
    else:
        print("")
        raise SystemExit(0)

if isinstance(cur, bool):
    print("true" if cur else "false")
elif cur is None:
    print("null")
else:
    print(cur)
PY
}

resolve_plugin_request_file() {
  local id="${1:-}"
  [[ -n "$id" ]] || { echo "ERROR: plugin request id/file required" >&2; exit 2; }

  local file="$id"
  [[ -f "$file" ]] || file="${BASE_DIR}/plugin-requests/${id%.json}.json"
  [[ -f "$file" ]] || file="${BASE_DIR}/plugin-requests/PLUGIN-REQUEST-${id#PLUGIN-REQUEST-}.json"

  [[ -f "$file" ]] || {
    echo "ERROR: plugin request not found: $id" >&2
    exit 2
  }

  printf '%s' "$file"
}

resolve_preflight_file() {
  local id="${1:-}"
  [[ -n "$id" ]] || { echo "ERROR: preflight id/file required" >&2; exit 2; }

  local file="$id"
  [[ -f "$file" ]] || file="${PREFLIGHT_DIR}/${id%.json}.json"
  [[ -f "$file" ]] || file="${PREFLIGHT_DIR}/EXECUTOR-PREFLIGHT-${id#EXECUTOR-PREFLIGHT-}.json"

  [[ -f "$file" ]] || {
    echo "ERROR: executor preflight not found: $id" >&2
    exit 2
  }

  printf '%s' "$file"
}

assert_eq() {
  local actual="$1" expected="$2" label="$3"
  [[ "$actual" == "$expected" ]] || {
    echo "ERROR: ${label}: expected ${expected}, got ${actual:-<missing>}" >&2
    exit 2
  }
}

assert_false() {
  local actual="$1" label="$2"
  assert_eq "$actual" "false" "$label"
}

verify_sources() {
  local request="$1"

  [[ -f "$POLICY_FILE" ]] || { echo "ERROR: missing action policy: $POLICY_FILE" >&2; exit 2; }
  [[ -f "$REGISTRY_FILE" ]] || { echo "ERROR: missing plugin registry: $REGISTRY_FILE" >&2; exit 2; }

  assert_eq "$(json_get "$request" schema)" "spot.plugin_request.v1" "plugin request schema"
  assert_eq "$(json_get "$request" request_status)" "closed_no_execution" "plugin request status"
  assert_false "$(json_get "$request" plugin_execution_allowed)" "plugin request plugin_execution_allowed"
  assert_false "$(json_get "$request" execution_allowed)" "plugin request execution_allowed"
  assert_false "$(json_get "$request" mutation_allowed)" "plugin request mutation_allowed"
  assert_false "$(json_get "$request" mutation_performed)" "plugin request mutation_performed"
  assert_false "$(json_get "$request" backup_bound)" "plugin request backup_bound"
  assert_eq "$(json_get "$request" next_allowed_action)" "manual_review_only" "plugin request next_allowed_action"

  assert_eq "$(json_get "$REGISTRY_FILE" schema)" "spot.plugin_registry.v1" "plugin registry schema"
  assert_eq "$(json_get "$REGISTRY_FILE" registry_status)" "locked_non_executing" "plugin registry status"
  assert_false "$(json_get "$REGISTRY_FILE" mutation_plugins_enabled)" "registry mutation_plugins_enabled"
  assert_false "$(json_get "$REGISTRY_FILE" plugin_execution_enabled)" "registry plugin_execution_enabled"

  assert_eq "$(json_get "$POLICY_FILE" schema)" "spot.action_policy.v1" "action policy schema"
  assert_eq "$(json_get "$POLICY_FILE" policy_status)" "locked" "action policy status"
  assert_false "$(json_get "$POLICY_FILE" mutation_plugins_enabled)" "policy mutation_plugins_enabled"

  local plugin action_class
  plugin="$(json_get "$request" plugin_name)"
  action_class="$(json_get "$request" action_class)"

  [[ -n "$plugin" ]] || { echo "ERROR: plugin_name missing from request" >&2; exit 2; }
  [[ -n "$action_class" ]] || { echo "ERROR: action_class missing from request" >&2; exit 2; }

  local plugin_status plugin_exec plugin_mut action_mut
  plugin_status="$(json_get "$REGISTRY_FILE" "plugins.${plugin}.status")"
  plugin_exec="$(json_get "$REGISTRY_FILE" "plugins.${plugin}.execution_allowed")"
  plugin_mut="$(json_get "$REGISTRY_FILE" "plugins.${plugin}.mutation_allowed")"
  action_mut="$(json_get "$POLICY_FILE" "action_classes.${action_class}.mutation_allowed")"

  case "$plugin_status" in
    disabled|forbidden) ;;
    "") echo "ERROR: plugin not found in registry: $plugin" >&2; exit 2 ;;
    *) echo "ERROR: plugin status must be disabled|forbidden, got $plugin_status" >&2; exit 2 ;;
  esac

  assert_false "$plugin_exec" "registry plugin execution_allowed"
  assert_false "$plugin_mut" "registry plugin mutation_allowed"
  assert_false "$action_mut" "policy action class mutation_allowed"
}

cmd_create() {
  need_cmd python3
  mkdir -p "$PREFLIGHT_DIR"

  local request ts req_id out
  request="$(resolve_plugin_request_file "${1:-}")"
  verify_sources "$request"

  ts="$(stamp)"
  req_id="$(json_get "$request" plugin_request_id)"
  out="${PREFLIGHT_DIR}/EXECUTOR-PREFLIGHT-${ts}-${req_id}.json"

  python3 - "$request" "$POLICY_FILE" "$REGISTRY_FILE" "$out" <<'PY'
import json, sys
from pathlib import Path
from datetime import datetime, UTC

request_path = Path(sys.argv[1])
policy_path = Path(sys.argv[2])
registry_path = Path(sys.argv[3])
out_path = Path(sys.argv[4])

request = json.loads(request_path.read_text())
policy = json.loads(policy_path.read_text())
registry = json.loads(registry_path.read_text())

plugin_name = request["plugin_name"]
action_class = request["action_class"]
plugin = registry["plugins"][plugin_name]
action = policy["action_classes"][action_class]

artifact = {
  "schema": "spot.executor_preflight.v1",
  "phase": "2.14",
  "created_utc": datetime.now(UTC).strftime("%Y%m%d-%H%M%S"),
  "mode": "dry_run_only",
  "preflight_status": "closed_blocked_no_execution",
  "linked_plugin_request": request["plugin_request_id"],
  "linked_action_handoff": request.get("linked_action_handoff"),
  "linked_action_request": request.get("linked_action_request"),
  "target": request.get("target"),
  "plugin_name": plugin_name,
  "action_class": action_class,
  "risk_class": request.get("risk_class"),
  "source_files": {
    "plugin_request": str(request_path),
    "plugin_registry": str(registry_path),
    "action_policy": str(policy_path)
  },
  "source_verification": {
    "plugin_request_verified": True,
    "plugin_registry_verified": True,
    "action_policy_verified": True,
    "registry_status": registry.get("registry_status"),
    "policy_status": policy.get("policy_status"),
    "plugin_status": plugin.get("status"),
    "action_policy_status": action.get("status")
  },
  "phase_2_14_execution_gate": {
    "dry_run_only": True,
    "produce_preflight_artifact_only": True,
    "execution_allowed": False,
    "mutation_allowed": False,
    "mutation_performed": False,
    "plugin_execution_allowed": False,
    "plugin_execution_enabled": False,
    "mutation_plugins_enabled": False,
    "executor_dispatch_allowed": False,
    "service_restart_allowed": False,
    "config_write_allowed": False,
    "network_mutation_allowed": False,
    "backup_binding_active": False
  },
  "policy_guards": {
    "primary_rule": policy.get("primary_rule"),
    "no_backup_no_change": True,
    "backup_required_before_mutation": policy.get("global_guards", {}).get("backup_required_before_mutation"),
    "backup_delete_allowed": policy.get("global_guards", {}).get("backup_delete_allowed"),
    "backup_overwrite_allowed": policy.get("global_guards", {}).get("backup_overwrite_allowed"),
    "freeform_shell_forbidden": registry.get("global_guards", {}).get("freeform_shell_forbidden"),
    "network_mutation_forbidden": registry.get("global_guards", {}).get("network_mutation_forbidden")
  },
  "result": {
    "ok": True,
    "blocked": True,
    "reason": "phase_2_14_preflight_artifact_only_no_execution"
  },
  "notes": [
    "This artifact proves preflight source verification only.",
    "This artifact does not authorize execution.",
    "This artifact does not bind a backup.",
    "This artifact does not restart services.",
    "This artifact does not write configuration.",
    "This artifact does not perform network mutation.",
    "Future execution requires a separate reviewed phase with backup binding, validation, rollback, append-only logs, and explicit plugin allowlist enforcement."
  ]
}

out_path.write_text(json.dumps(artifact, indent=2) + "\n")
PY

  cmd_verify "$out" >/dev/null
  echo "$out"
}

cmd_verify() {
  need_cmd python3
  local file
  file="$(resolve_preflight_file "${1:-}")"

  assert_eq "$(json_get "$file" schema)" "spot.executor_preflight.v1" "preflight schema"
  assert_eq "$(json_get "$file" phase)" "2.14" "preflight phase"
  assert_eq "$(json_get "$file" mode)" "dry_run_only" "preflight mode"
  assert_eq "$(json_get "$file" preflight_status)" "closed_blocked_no_execution" "preflight status"

  assert_eq "$(json_get "$file" source_verification.plugin_request_verified)" "true" "plugin request verified"
  assert_eq "$(json_get "$file" source_verification.plugin_registry_verified)" "true" "plugin registry verified"
  assert_eq "$(json_get "$file" source_verification.action_policy_verified)" "true" "action policy verified"

  assert_eq "$(json_get "$file" phase_2_14_execution_gate.dry_run_only)" "true" "dry_run_only"
  assert_eq "$(json_get "$file" phase_2_14_execution_gate.produce_preflight_artifact_only)" "true" "produce_preflight_artifact_only"

  assert_false "$(json_get "$file" phase_2_14_execution_gate.execution_allowed)" "execution_allowed"
  assert_false "$(json_get "$file" phase_2_14_execution_gate.mutation_allowed)" "mutation_allowed"
  assert_false "$(json_get "$file" phase_2_14_execution_gate.mutation_performed)" "mutation_performed"
  assert_false "$(json_get "$file" phase_2_14_execution_gate.plugin_execution_allowed)" "plugin_execution_allowed"
  assert_false "$(json_get "$file" phase_2_14_execution_gate.plugin_execution_enabled)" "plugin_execution_enabled"
  assert_false "$(json_get "$file" phase_2_14_execution_gate.mutation_plugins_enabled)" "mutation_plugins_enabled"
  assert_false "$(json_get "$file" phase_2_14_execution_gate.executor_dispatch_allowed)" "executor_dispatch_allowed"
  assert_false "$(json_get "$file" phase_2_14_execution_gate.service_restart_allowed)" "service_restart_allowed"
  assert_false "$(json_get "$file" phase_2_14_execution_gate.config_write_allowed)" "config_write_allowed"
  assert_false "$(json_get "$file" phase_2_14_execution_gate.network_mutation_allowed)" "network_mutation_allowed"
  assert_false "$(json_get "$file" phase_2_14_execution_gate.backup_binding_active)" "backup_binding_active"

  assert_eq "$(json_get "$file" result.ok)" "true" "result ok"
  assert_eq "$(json_get "$file" result.blocked)" "true" "result blocked"

  echo "OK: executor preflight verified: $file"
}

cmd_show() {
  local file
  file="$(resolve_preflight_file "${1:-}")"
  cat "$file"
}

cmd_list() {
  local count="${1:-20}"
  mkdir -p "$PREFLIGHT_DIR"
  find "$PREFLIGHT_DIR" -maxdepth 1 -type f -name 'EXECUTOR-PREFLIGHT-*.json' -printf '%T@ %p\n' \
    | sort -nr \
    | head -n "$count" \
    | cut -d' ' -f2-
}


cmd_summary() {
  need_cmd python3
  mkdir -p "$PREFLIGHT_DIR" "$STATE_DIR"

  python3 - "$PREFLIGHT_DIR" "$SUMMARY_FILE" <<'SUMMARY_PY'
import json
import sys
from pathlib import Path
from datetime import datetime, UTC

preflight_dir = Path(sys.argv[1])
summary_file = Path(sys.argv[2])

gate_keys = [
    "execution_allowed",
    "mutation_allowed",
    "mutation_performed",
    "plugin_execution_allowed",
    "plugin_execution_enabled",
    "mutation_plugins_enabled",
    "executor_dispatch_allowed",
    "service_restart_allowed",
    "config_write_allowed",
    "network_mutation_allowed",
    "backup_binding_active",
]

items = []
for path in sorted(preflight_dir.glob("EXECUTOR-PREFLIGHT-*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
    try:
        data = json.loads(path.read_text())
        gate = data.get("phase_2_14_execution_gate", {})
        result = data.get("result", {})
        item = {
            "file": str(path),
            "name": path.name,
            "mtime": int(path.stat().st_mtime),
            "schema": data.get("schema"),
            "phase": data.get("phase"),
            "created_utc": data.get("created_utc"),
            "mode": data.get("mode"),
            "preflight_status": data.get("preflight_status"),
            "linked_plugin_request": data.get("linked_plugin_request"),
            "plugin_name": data.get("plugin_name"),
            "action_class": data.get("action_class"),
            "risk_class": data.get("risk_class"),
            "ok": result.get("ok"),
            "blocked": result.get("blocked"),
            "reason": result.get("reason"),
        }
        for key in gate_keys:
            item[key] = gate.get(key)
        items.append(item)
    except Exception as exc:
        items.append({
            "file": str(path),
            "name": path.name,
            "mtime": int(path.stat().st_mtime),
            "parse_error": repr(exc),
            "ok": False,
            "blocked": None,
        })

def is_verified(item):
    return (
        item.get("schema") == "spot.executor_preflight.v1"
        and item.get("mode") == "dry_run_only"
        and item.get("ok") is True
        and item.get("blocked") is True
        and all(item.get(key) is False for key in gate_keys)
    )

verified_items = [item for item in items if is_verified(item)]

summary = {
    "schema": "spot.executor_preflight_summary.v1",
    "created_utc": datetime.now(UTC).strftime("%Y%m%d-%H%M%S"),
    "preflight_dir": str(preflight_dir),
    "summary_file": str(summary_file),
    "count": len(items),
    "verified_count": len(verified_items),
    "invalid_count": len(items) - len(verified_items),
    "newest": items[0] if items else None,
    "hard_gate_keys": gate_keys,
    "all_known_preflights_blocked_and_non_mutating": len(items) == len(verified_items),
    "items": items[:25],
}

summary_file.write_text(json.dumps(summary, indent=2) + "\n")
print(json.dumps(summary, indent=2))
SUMMARY_PY
}

main() {
  local cmd="${1:-}"
  shift || true

  case "$cmd" in
    create) cmd_create "$@" ;;
    verify) cmd_verify "$@" ;;
    show) cmd_show "$@" ;;
    list) cmd_list "$@" ;;
    summary) cmd_summary "$@" ;;
    -h|--help|help|"") usage ;;
    *) echo "ERROR: unknown command: $cmd" >&2; usage >&2; exit 2 ;;
  esac
}

main "$@"
