#!/usr/bin/env bash
set -Eeuo pipefail

BASE_DIR="${BASE_DIR:-/home/ogre/spot-stack/watch}"
CONTRACT_DIR="${CONTRACT_DIR:-${BASE_DIR}/backup-artifact-manifest-contracts}"
STATE_DIR="${STATE_DIR:-${BASE_DIR}/state}"
SUMMARY_FILE="${SUMMARY_FILE:-${STATE_DIR}/backup-artifact-manifest-contract-summary.json}"
BACKUP_BINDING_CONTRACT_SCRIPT="${BACKUP_BINDING_CONTRACT_SCRIPT:-${BASE_DIR}/spot-backup-binding-contract.sh}"

usage() {
  cat <<'USAGE'
Usage:
  spot-backup-artifact-manifest-contract.sh create-design <backup-binding-contract-id-or-file>
  spot-backup-artifact-manifest-contract.sh verify <manifest-contract-id-or-file>
  spot-backup-artifact-manifest-contract.sh show <manifest-contract-id-or-file>
  spot-backup-artifact-manifest-contract.sh list [count]
  spot-backup-artifact-manifest-contract.sh summary

Phase 2.22 only:
- designs future backup artifact manifest contract artifacts
- requires linked backup-binding contract verification
- performs no backup creation
- performs no checksum generation over live data
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

resolve_binding_contract_file() {
  local id="${1:-}"
  [[ -n "$id" ]] || { echo "ERROR: backup-binding contract id/file required" >&2; exit 2; }

  local file="$id"
  [[ -f "$file" ]] || file="${BASE_DIR}/backup-binding-contracts/${id%.json}.json"
  [[ -f "$file" ]] || file="${BASE_DIR}/backup-binding-contracts/BACKUP-BINDING-CONTRACT-${id#BACKUP-BINDING-CONTRACT-}.json"

  [[ -f "$file" ]] || {
    echo "ERROR: backup-binding contract not found: $id" >&2
    exit 2
  }

  printf '%s' "$file"
}

resolve_manifest_contract_file() {
  local id="${1:-}"
  [[ -n "$id" ]] || { echo "ERROR: backup artifact manifest contract id/file required" >&2; exit 2; }

  local file="$id"
  [[ -f "$file" ]] || file="${CONTRACT_DIR}/${id%.json}.json"
  [[ -f "$file" ]] || file="${CONTRACT_DIR}/BACKUP-ARTIFACT-MANIFEST-CONTRACT-${id#BACKUP-ARTIFACT-MANIFEST-CONTRACT-}.json"

  [[ -f "$file" ]] || {
    echo "ERROR: backup artifact manifest contract not found: $id" >&2
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
  need_file "$BACKUP_BINDING_CONTRACT_SCRIPT"
  mkdir -p "$CONTRACT_DIR"

  local binding_contract ts binding_name binding_hash short_ref out
  binding_contract="$(resolve_binding_contract_file "${1:-}")"

  "$BACKUP_BINDING_CONTRACT_SCRIPT" verify "$binding_contract" >/dev/null

  ts="$(stamp)"
  binding_name="$(basename "$binding_contract" .json)"
  binding_hash="$(printf '%s' "$binding_name" | sha256sum | awk '{print substr($1,1,12)}')"
  short_ref="$(printf '%s' "$binding_name" | sed -E 's/^(BACKUP-BINDING-CONTRACT-[0-9]{8}-[0-9]{6}).*/\1/')"
  out="${CONTRACT_DIR}/BACKUP-ARTIFACT-MANIFEST-CONTRACT-${ts}-${short_ref}-${binding_hash}.json"

  python3 - "$binding_contract" "$out" <<'PY'
import json
import sys
from pathlib import Path
from datetime import datetime, UTC

binding_path = Path(sys.argv[1])
out_path = Path(sys.argv[2])
binding = json.loads(binding_path.read_text())

artifact = {
  "schema": "spot.backup_artifact_manifest_contract.v1",
  "phase": "2.22",
  "created_utc": datetime.now(UTC).strftime("%Y%m%d-%H%M%S"),
  "mode": "manifest_contract_design_only",
  "contract_status": "draft_manifest_design_no_backup_creation",
  "linked_backup_binding_contract": binding_path.name,
  "linked_backup_binding_contract_file": str(binding_path),
  "linked_executor_preflight": binding.get("linked_executor_preflight"),
  "linked_plugin_request": binding.get("linked_plugin_request"),
  "linked_action_handoff": binding.get("linked_action_handoff"),
  "linked_action_request": binding.get("linked_action_request"),
  "target": binding.get("target"),
  "plugin_name": binding.get("plugin_name"),
  "action_class": binding.get("action_class"),
  "risk_class": binding.get("risk_class"),
  "future_backup_artifact_manifest": {
    "manifest_required_before_backup_binding": True,
    "manifest_filename": "metadata.json",
    "checksum_filename": "SHA256SUMS",
    "required_manifest_fields": [
      "schema",
      "created_utc",
      "target",
      "service",
      "action_class",
      "risk_class",
      "source_policy",
      "executor_preflight_file",
      "backup_binding_contract_file",
      "backup_artifact_path",
      "artifact_inventory",
      "checksum_file",
      "checksum_algorithm",
      "verification_result",
      "rollback_authority",
      "restore_without_recorded_artifact_allowed",
      "mutation_allowed",
      "execution_allowed"
    ],
    "required_artifact_inventory_fields": [
      "relative_path",
      "artifact_type",
      "size_bytes",
      "sha256",
      "source_path",
      "capture_mode"
    ],
    "required_verification_checks": [
      "manifest_json_valid",
      "manifest_schema_valid",
      "required_manifest_fields_present",
      "artifact_inventory_non_empty",
      "artifact_inventory_paths_relative",
      "checksum_file_present",
      "checksum_algorithm_sha256",
      "checksum_entries_match_inventory",
      "backup_artifact_path_recorded",
      "rollback_authority_recorded_prechange_backup_only"
    ],
    "allowed_checksum_algorithm": "sha256",
    "rollback_authority": "recorded_prechange_backup_only",
    "restore_without_recorded_artifact_allowed": False,
    "backup_delete_allowed": False,
    "backup_overwrite_allowed": False
  },
  "phase_2_22_manifest_design_gate": {
    "design_only": True,
    "manifest_contract_only": True,
    "backup_manifest_created": False,
    "backup_artifact_created": False,
    "checksum_generated": False,
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
    "reason": "phase_2_22_backup_artifact_manifest_contract_design_only_no_backup_creation"
  },
  "notes": [
    "This artifact defines the future backup artifact manifest contract shape only.",
    "This artifact does not create metadata.json.",
    "This artifact does not create SHA256SUMS.",
    "This artifact does not inspect or checksum live files.",
    "This artifact does not create a backup.",
    "This artifact does not bind a backup.",
    "This artifact does not authorize execution.",
    "Future live backup artifact creation requires a separate reviewed implementation slice."
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
  file="$(resolve_manifest_contract_file "${1:-}")"

  assert_eq "$(json_get "$file" schema)" "spot.backup_artifact_manifest_contract.v1" "manifest contract schema"
  assert_eq "$(json_get "$file" phase)" "2.22" "manifest contract phase"
  assert_eq "$(json_get "$file" mode)" "manifest_contract_design_only" "manifest contract mode"
  assert_eq "$(json_get "$file" contract_status)" "draft_manifest_design_no_backup_creation" "manifest contract status"

  assert_true "$(json_get "$file" future_backup_artifact_manifest.manifest_required_before_backup_binding)" "manifest_required_before_backup_binding"
  assert_eq "$(json_get "$file" future_backup_artifact_manifest.manifest_filename)" "metadata.json" "manifest_filename"
  assert_eq "$(json_get "$file" future_backup_artifact_manifest.checksum_filename)" "SHA256SUMS" "checksum_filename"
  assert_eq "$(json_get "$file" future_backup_artifact_manifest.allowed_checksum_algorithm)" "sha256" "allowed_checksum_algorithm"
  assert_eq "$(json_get "$file" future_backup_artifact_manifest.rollback_authority)" "recorded_prechange_backup_only" "rollback_authority"
  assert_false "$(json_get "$file" future_backup_artifact_manifest.restore_without_recorded_artifact_allowed)" "restore_without_recorded_artifact_allowed"
  assert_false "$(json_get "$file" future_backup_artifact_manifest.backup_delete_allowed)" "backup_delete_allowed"
  assert_false "$(json_get "$file" future_backup_artifact_manifest.backup_overwrite_allowed)" "backup_overwrite_allowed"

  assert_true "$(json_get "$file" phase_2_22_manifest_design_gate.design_only)" "design_only"
  assert_true "$(json_get "$file" phase_2_22_manifest_design_gate.manifest_contract_only)" "manifest_contract_only"
  assert_false "$(json_get "$file" phase_2_22_manifest_design_gate.backup_manifest_created)" "backup_manifest_created"
  assert_false "$(json_get "$file" phase_2_22_manifest_design_gate.backup_artifact_created)" "backup_artifact_created"
  assert_false "$(json_get "$file" phase_2_22_manifest_design_gate.checksum_generated)" "checksum_generated"
  assert_false "$(json_get "$file" phase_2_22_manifest_design_gate.backup_creation_allowed)" "backup_creation_allowed"
  assert_false "$(json_get "$file" phase_2_22_manifest_design_gate.backup_binding_active)" "backup_binding_active"
  assert_false "$(json_get "$file" phase_2_22_manifest_design_gate.backup_verified)" "backup_verified"
  assert_false "$(json_get "$file" phase_2_22_manifest_design_gate.execution_allowed)" "execution_allowed"
  assert_false "$(json_get "$file" phase_2_22_manifest_design_gate.mutation_allowed)" "mutation_allowed"
  assert_false "$(json_get "$file" phase_2_22_manifest_design_gate.mutation_performed)" "mutation_performed"
  assert_false "$(json_get "$file" phase_2_22_manifest_design_gate.executor_dispatch_allowed)" "executor_dispatch_allowed"
  assert_false "$(json_get "$file" phase_2_22_manifest_design_gate.service_restart_allowed)" "service_restart_allowed"
  assert_false "$(json_get "$file" phase_2_22_manifest_design_gate.config_write_allowed)" "config_write_allowed"
  assert_false "$(json_get "$file" phase_2_22_manifest_design_gate.network_mutation_allowed)" "network_mutation_allowed"

  assert_true "$(json_get "$file" result.ok)" "result ok"
  assert_true "$(json_get "$file" result.blocked)" "result blocked"

  echo "OK: backup artifact manifest contract verified: $file"
}

cmd_show() {
  local file
  file="$(resolve_manifest_contract_file "${1:-}")"
  cat "$file"
}

cmd_list() {
  local count="${1:-20}"
  mkdir -p "$CONTRACT_DIR"
  find "$CONTRACT_DIR" -maxdepth 1 -type f -name 'BACKUP-ARTIFACT-MANIFEST-CONTRACT-*.json' -printf '%T@ %p\n' \
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
    "backup_manifest_created",
    "backup_artifact_created",
    "checksum_generated",
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
for path in sorted(contract_dir.glob("BACKUP-ARTIFACT-MANIFEST-CONTRACT-*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
    try:
        data = json.loads(path.read_text())
        gate = data.get("phase_2_22_manifest_design_gate", {})
        manifest = data.get("future_backup_artifact_manifest", {})
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
            "linked_backup_binding_contract": data.get("linked_backup_binding_contract"),
            "linked_executor_preflight": data.get("linked_executor_preflight"),
            "linked_plugin_request": data.get("linked_plugin_request"),
            "plugin_name": data.get("plugin_name"),
            "action_class": data.get("action_class"),
            "risk_class": data.get("risk_class"),
            "ok": result.get("ok"),
            "blocked": result.get("blocked"),
            "reason": result.get("reason"),
            "manifest_required_before_backup_binding": manifest.get("manifest_required_before_backup_binding"),
            "manifest_filename": manifest.get("manifest_filename"),
            "checksum_filename": manifest.get("checksum_filename"),
            "allowed_checksum_algorithm": manifest.get("allowed_checksum_algorithm"),
            "rollback_authority": manifest.get("rollback_authority"),
            "backup_delete_allowed": manifest.get("backup_delete_allowed"),
            "backup_overwrite_allowed": manifest.get("backup_overwrite_allowed"),
            "restore_without_recorded_artifact_allowed": manifest.get("restore_without_recorded_artifact_allowed"),
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
        item.get("schema") == "spot.backup_artifact_manifest_contract.v1"
        and item.get("phase") == "2.22"
        and item.get("mode") == "manifest_contract_design_only"
        and item.get("contract_status") == "draft_manifest_design_no_backup_creation"
        and item.get("ok") is True
        and item.get("blocked") is True
        and item.get("manifest_required_before_backup_binding") is True
        and item.get("manifest_filename") == "metadata.json"
        and item.get("checksum_filename") == "SHA256SUMS"
        and item.get("allowed_checksum_algorithm") == "sha256"
        and item.get("rollback_authority") == "recorded_prechange_backup_only"
        and item.get("backup_delete_allowed") is False
        and item.get("backup_overwrite_allowed") is False
        and item.get("restore_without_recorded_artifact_allowed") is False
        and all(item.get(key) is False for key in gate_keys)
    )

verified_items = [item for item in items if is_verified(item)]

summary = {
    "schema": "spot.backup_artifact_manifest_contract_summary.v1",
    "created_utc": datetime.now(UTC).strftime("%Y%m%d-%H%M%S"),
    "contract_dir": str(contract_dir),
    "summary_file": str(summary_file),
    "count": len(items),
    "verified_count": len(verified_items),
    "invalid_count": len(items) - len(verified_items),
    "newest": items[0] if items else None,
    "hard_gate_keys": gate_keys,
    "all_known_manifest_contracts_design_only_blocked_and_non_mutating": len(items) == len(verified_items),
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
