#!/usr/bin/env bash
set -Eeuo pipefail

BASE_DIR="${BASE_DIR:-/home/ogre/spot-stack/watch}"
CONTRACT_DIR="${CONTRACT_DIR:-${BASE_DIR}/backup-binding-contracts}"
STATE_DIR="${STATE_DIR:-${BASE_DIR}/state}"
SUMMARY_FILE="${SUMMARY_FILE:-${STATE_DIR}/backup-binding-contract-summary.json}"
PREFLIGHT_SCRIPT="${PREFLIGHT_SCRIPT:-${BASE_DIR}/spot-executor-preflight.sh}"

usage() {
  cat <<'USAGE'
Usage:
  spot-backup-binding-contract.sh create-design <executor-preflight-id-or-file>
  spot-backup-binding-contract.sh verify <contract-id-or-file>
  spot-backup-binding-contract.sh show <contract-id-or-file>
  spot-backup-binding-contract.sh list [count]
  spot-backup-binding-contract.sh summary

Phase 2.18 only:
- designs future backup-binding contract artifacts
- requires linked executor preflight verification
- performs no backup creation
- performs no live backup binding
- performs no mutation, execution, service restart, config write, network change, or executor dispatch
USAGE
}

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "ERROR: required command not found: $1" >&2
    exit 2
  }
}

need_file() {
  local file="$1"
  [[ -f "$file" ]] || {
    echo "ERROR: required file not found: $file" >&2
    exit 2
  }
}

stamp() { date -u +%Y%m%d-%H%M%S; }

json_get() {
  local file="$1" expr="$2"
  python3 - "$file" "$expr" <<'PY'
import json
import sys
from pathlib import Path

data = json.loads(Path(sys.argv[1]).read_text())
cur = data
for part in sys.argv[2].split("."):
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

resolve_preflight_file() {
  local id="${1:-}"
  [[ -n "$id" ]] || { echo "ERROR: executor preflight id/file required" >&2; exit 2; }

  local file="$id"
  [[ -f "$file" ]] || file="${BASE_DIR}/executor-preflights/${id%.json}.json"
  [[ -f "$file" ]] || file="${BASE_DIR}/executor-preflights/EXECUTOR-PREFLIGHT-${id#EXECUTOR-PREFLIGHT-}.json"

  [[ -f "$file" ]] || {
    echo "ERROR: executor preflight not found: $id" >&2
    exit 2
  }

  printf '%s' "$file"
}

resolve_contract_file() {
  local id="${1:-}"
  [[ -n "$id" ]] || { echo "ERROR: backup-binding contract id/file required" >&2; exit 2; }

  local file="$id"
  [[ -f "$file" ]] || file="${CONTRACT_DIR}/${id%.json}.json"
  [[ -f "$file" ]] || file="${CONTRACT_DIR}/BACKUP-BINDING-CONTRACT-${id#BACKUP-BINDING-CONTRACT-}.json"

  [[ -f "$file" ]] || {
    echo "ERROR: backup-binding contract not found: $id" >&2
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

assert_true() {
  local actual="$1" label="$2"
  assert_eq "$actual" "true" "$label"
}

cmd_create_design() {
  need_cmd python3
  need_file "$PREFLIGHT_SCRIPT"
  mkdir -p "$CONTRACT_DIR"

  local preflight ts preflight_name out
  preflight="$(resolve_preflight_file "${1:-}")"

  "$PREFLIGHT_SCRIPT" verify "$preflight" >/dev/null

  ts="$(stamp)"
  preflight_name="$(basename "$preflight" .json)"
  out="${CONTRACT_DIR}/BACKUP-BINDING-CONTRACT-${ts}-${preflight_name}.json"

  python3 - "$preflight" "$out" <<'PY'
import json
import sys
from pathlib import Path
from datetime import datetime, UTC

preflight_path = Path(sys.argv[1])
out_path = Path(sys.argv[2])
preflight = json.loads(preflight_path.read_text())

artifact = {
  "schema": "spot.backup_binding_contract.v1",
  "phase": "2.18",
  "created_utc": datetime.now(UTC).strftime("%Y%m%d-%H%M%S"),
  "mode": "contract_design_only",
  "contract_status": "draft_design_no_binding",
  "linked_executor_preflight": preflight_path.name,
  "linked_executor_preflight_file": str(preflight_path),
  "linked_plugin_request": preflight.get("linked_plugin_request"),
  "linked_action_handoff": preflight.get("linked_action_handoff"),
  "linked_action_request": preflight.get("linked_action_request"),
  "target": preflight.get("target"),
  "plugin_name": preflight.get("plugin_name"),
  "action_class": preflight.get("action_class"),
  "risk_class": preflight.get("risk_class"),
  "future_backup_contract": {
    "backup_required_before_mutation": True,
    "backup_root_required": "/mnt/collective/backups/",
    "target_path_template": "/mnt/collective/backups/<target>/<service>/<timestamp>/",
    "required_artifacts": [
      "metadata.json",
      "SHA256SUMS",
      "prechange_files_or_state_snapshot",
      "linked_executor_preflight",
      "linked_backup_binding_contract"
    ],
    "required_metadata_fields": [
      "created_utc",
      "target",
      "service",
      "action_class",
      "risk_class",
      "source_policy",
      "executor_preflight_file",
      "backup_artifact_path",
      "checksum_file",
      "verification_result",
      "rollback_authority"
    ],
    "verification_requirements": [
      "backup_directory_exists",
      "required_artifacts_present",
      "metadata_json_valid",
      "sha256sums_valid",
      "backup_path_readable",
      "backup_path_recorded_before_execution"
    ],
    "rollback_authority": "recorded_prechange_backup_only",
    "restore_without_recorded_artifact_allowed": False,
    "backup_delete_allowed": False,
    "backup_overwrite_allowed": False
  },
  "phase_2_18_design_gate": {
    "design_only": True,
    "backup_creation_allowed": False,
    "backup_binding_active": False,
    "backup_verified": False,
    "execution_allowed": False,
    "mutation_allowed": False,
    "mutation_performed": False,
    "executor_dispatch_allowed": False,
    "service_restart_allowed": False,
    "config_write_allowed": False,
    "network_mutation_allowed": False
  },
  "result": {
    "ok": True,
    "blocked": True,
    "reason": "phase_2_18_backup_binding_contract_design_only_no_live_binding"
  },
  "notes": [
    "This artifact defines the future backup-binding contract shape only.",
    "This artifact does not create a backup.",
    "This artifact does not bind a backup.",
    "This artifact does not authorize execution.",
    "This artifact does not perform mutation.",
    "Future live backup binding requires a separate reviewed implementation slice."
  ]
}

out_path.write_text(json.dumps(artifact, indent=2) + "\n")
print(out_path)
PY

  cmd_verify "$out" >/dev/null
  echo "$out"
}

cmd_verify() {
  need_cmd python3
  local file
  file="$(resolve_contract_file "${1:-}")"

  assert_eq "$(json_get "$file" schema)" "spot.backup_binding_contract.v1" "contract schema"
  assert_eq "$(json_get "$file" phase)" "2.18" "contract phase"
  assert_eq "$(json_get "$file" mode)" "contract_design_only" "contract mode"
  assert_eq "$(json_get "$file" contract_status)" "draft_design_no_binding" "contract status"

  assert_true "$(json_get "$file" future_backup_contract.backup_required_before_mutation)" "backup_required_before_mutation"
  assert_eq "$(json_get "$file" future_backup_contract.backup_root_required)" "/mnt/collective/backups/" "backup_root_required"
  assert_eq "$(json_get "$file" future_backup_contract.rollback_authority)" "recorded_prechange_backup_only" "rollback_authority"
  assert_false "$(json_get "$file" future_backup_contract.restore_without_recorded_artifact_allowed)" "restore_without_recorded_artifact_allowed"
  assert_false "$(json_get "$file" future_backup_contract.backup_delete_allowed)" "backup_delete_allowed"
  assert_false "$(json_get "$file" future_backup_contract.backup_overwrite_allowed)" "backup_overwrite_allowed"

  assert_true "$(json_get "$file" phase_2_18_design_gate.design_only)" "design_only"
  assert_false "$(json_get "$file" phase_2_18_design_gate.backup_creation_allowed)" "backup_creation_allowed"
  assert_false "$(json_get "$file" phase_2_18_design_gate.backup_binding_active)" "backup_binding_active"
  assert_false "$(json_get "$file" phase_2_18_design_gate.backup_verified)" "backup_verified"
  assert_false "$(json_get "$file" phase_2_18_design_gate.execution_allowed)" "execution_allowed"
  assert_false "$(json_get "$file" phase_2_18_design_gate.mutation_allowed)" "mutation_allowed"
  assert_false "$(json_get "$file" phase_2_18_design_gate.mutation_performed)" "mutation_performed"
  assert_false "$(json_get "$file" phase_2_18_design_gate.executor_dispatch_allowed)" "executor_dispatch_allowed"
  assert_false "$(json_get "$file" phase_2_18_design_gate.service_restart_allowed)" "service_restart_allowed"
  assert_false "$(json_get "$file" phase_2_18_design_gate.config_write_allowed)" "config_write_allowed"
  assert_false "$(json_get "$file" phase_2_18_design_gate.network_mutation_allowed)" "network_mutation_allowed"

  assert_true "$(json_get "$file" result.ok)" "result ok"
  assert_true "$(json_get "$file" result.blocked)" "result blocked"

  echo "OK: backup-binding contract verified: $file"
}

cmd_show() {
  local file
  file="$(resolve_contract_file "${1:-}")"
  cat "$file"
}

cmd_list() {
  local count="${1:-20}"
  mkdir -p "$CONTRACT_DIR"
  find "$CONTRACT_DIR" -maxdepth 1 -type f -name 'BACKUP-BINDING-CONTRACT-*.json' -printf '%T@ %p\n' \
    | sort -nr \
    | head -n "$count" \
    | cut -d' ' -f2-
}


cmd_summary() {
  need_cmd python3
  mkdir -p "$CONTRACT_DIR" "$STATE_DIR"

  python3 - "$CONTRACT_DIR" "$SUMMARY_FILE" <<'SUMMARY_PY'
import json
import sys
from pathlib import Path
from datetime import datetime, UTC

contract_dir = Path(sys.argv[1])
summary_file = Path(sys.argv[2])

gate_keys = [
    "backup_creation_allowed",
    "backup_binding_active",
    "backup_verified",
    "execution_allowed",
    "mutation_allowed",
    "mutation_performed",
    "executor_dispatch_allowed",
    "service_restart_allowed",
    "config_write_allowed",
    "network_mutation_allowed",
]

items = []
for path in sorted(contract_dir.glob("BACKUP-BINDING-CONTRACT-*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
    try:
        data = json.loads(path.read_text())
        gate = data.get("phase_2_18_design_gate", {})
        future = data.get("future_backup_contract", {})
        result = data.get("result", {})
        item = {
            "file": str(path),
            "name": path.name,
            "mtime": int(path.stat().st_mtime),
            "schema": data.get("schema"),
            "phase": data.get("phase"),
            "created_utc": data.get("created_utc"),
            "mode": data.get("mode"),
            "contract_status": data.get("contract_status"),
            "linked_executor_preflight": data.get("linked_executor_preflight"),
            "linked_plugin_request": data.get("linked_plugin_request"),
            "plugin_name": data.get("plugin_name"),
            "action_class": data.get("action_class"),
            "risk_class": data.get("risk_class"),
            "ok": result.get("ok"),
            "blocked": result.get("blocked"),
            "reason": result.get("reason"),
            "backup_required_before_mutation": future.get("backup_required_before_mutation"),
            "rollback_authority": future.get("rollback_authority"),
            "backup_delete_allowed": future.get("backup_delete_allowed"),
            "backup_overwrite_allowed": future.get("backup_overwrite_allowed"),
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
        item.get("schema") == "spot.backup_binding_contract.v1"
        and item.get("phase") == "2.18"
        and item.get("mode") == "contract_design_only"
        and item.get("contract_status") == "draft_design_no_binding"
        and item.get("ok") is True
        and item.get("blocked") is True
        and item.get("backup_required_before_mutation") is True
        and item.get("rollback_authority") == "recorded_prechange_backup_only"
        and item.get("backup_delete_allowed") is False
        and item.get("backup_overwrite_allowed") is False
        and all(item.get(key) is False for key in gate_keys)
    )

verified_items = [item for item in items if is_verified(item)]

summary = {
    "schema": "spot.backup_binding_contract_summary.v1",
    "created_utc": datetime.now(UTC).strftime("%Y%m%d-%H%M%S"),
    "contract_dir": str(contract_dir),
    "summary_file": str(summary_file),
    "count": len(items),
    "verified_count": len(verified_items),
    "invalid_count": len(items) - len(verified_items),
    "newest": items[0] if items else None,
    "hard_gate_keys": gate_keys,
    "all_known_contracts_design_only_blocked_and_non_mutating": len(items) == len(verified_items),
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
    create-design) cmd_create_design "$@" ;;
    verify) cmd_verify "$@" ;;
    show) cmd_show "$@" ;;
    list) cmd_list "$@" ;;
    summary) cmd_summary "$@" ;;
    -h|--help|help|"") usage ;;
    *) echo "ERROR: unknown command: $cmd" >&2; usage >&2; exit 2 ;;
  esac
}

main "$@"
