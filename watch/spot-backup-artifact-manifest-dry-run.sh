#!/usr/bin/env bash
set -Eeuo pipefail

BASE_DIR="${BASE_DIR:-/home/ogre/spot-stack/watch}"
DRY_RUN_DIR="${DRY_RUN_DIR:-${BASE_DIR}/backup-artifact-manifest-dry-runs}"
MANIFEST_CONTRACT_SCRIPT="${MANIFEST_CONTRACT_SCRIPT:-${BASE_DIR}/spot-backup-artifact-manifest-contract.sh}"

usage() {
  cat <<'USAGE'
Usage:
  spot-backup-artifact-manifest-dry-run.sh create <backup-artifact-manifest-contract-id-or-file>
  spot-backup-artifact-manifest-dry-run.sh verify <dry-run-id-or-file>
  spot-backup-artifact-manifest-dry-run.sh show <dry-run-id-or-file>
  spot-backup-artifact-manifest-dry-run.sh list [count]

Phase 2.26 only:
- simulates future backup artifact manifest generation
- produces dry-run manifest artifacts only
- does not read or hash live target files
- does not create metadata.json or SHA256SUMS in a backup directory
- does not create backups
- does not bind backups
- does not execute, mutate, restart services, write configs, change network state, or dispatch executor actions
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

resolve_manifest_contract_file() {
  local id="${1:-}"
  [[ -n "$id" ]] || { echo "ERROR: backup artifact manifest contract id/file required" >&2; exit 2; }

  local file="$id"
  [[ -f "$file" ]] || file="${BASE_DIR}/backup-artifact-manifest-contracts/${id%.json}.json"
  [[ -f "$file" ]] || file="${BASE_DIR}/backup-artifact-manifest-contracts/BACKUP-ARTIFACT-MANIFEST-CONTRACT-${id#BACKUP-ARTIFACT-MANIFEST-CONTRACT-}.json"

  [[ -f "$file" ]] || {
    echo "ERROR: backup artifact manifest contract not found: $id" >&2
    exit 2
  }

  printf '%s' "$file"
}

resolve_dry_run_file() {
  local id="${1:-}"
  [[ -n "$id" ]] || { echo "ERROR: backup artifact manifest dry-run id/file required" >&2; exit 2; }

  local file="$id"
  [[ -f "$file" ]] || file="${DRY_RUN_DIR}/${id%.json}.json"
  [[ -f "$file" ]] || file="${DRY_RUN_DIR}/BACKUP-ARTIFACT-MANIFEST-DRY-RUN-${id#BACKUP-ARTIFACT-MANIFEST-DRY-RUN-}.json"

  [[ -f "$file" ]] || {
    echo "ERROR: backup artifact manifest dry-run not found: $id" >&2
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

cmd_create() {
  need_cmd python3
  need_file "$MANIFEST_CONTRACT_SCRIPT"
  mkdir -p "$DRY_RUN_DIR"

  local manifest_contract ts contract_name contract_hash short_ref out
  manifest_contract="$(resolve_manifest_contract_file "${1:-}")"

  "$MANIFEST_CONTRACT_SCRIPT" verify "$manifest_contract" >/dev/null

  ts="$(stamp)"
  contract_name="$(basename "$manifest_contract" .json)"
  contract_hash="$(printf '%s' "$contract_name" | sha256sum | awk '{print substr($1,1,12)}')"
  short_ref="$(printf '%s' "$contract_name" | sed -E 's/^(BACKUP-ARTIFACT-MANIFEST-CONTRACT-[0-9]{8}-[0-9]{6}).*/\1/')"
  out="${DRY_RUN_DIR}/BACKUP-ARTIFACT-MANIFEST-DRY-RUN-${ts}-${short_ref}-${contract_hash}.json"

  python3 - "$manifest_contract" "$out" <<'PY'
import json
import sys
from pathlib import Path
from datetime import datetime, UTC

contract_path = Path(sys.argv[1])
out_path = Path(sys.argv[2])
contract = json.loads(contract_path.read_text())
future = contract.get("future_backup_artifact_manifest", {})

# Synthetic placeholders only. These are not hashes of live files.
synthetic_inventory = [
    {
        "relative_path": "metadata.json",
        "artifact_type": "manifest_design_placeholder",
        "size_bytes": 0,
        "sha256": "SIMULATED-NOT-CALCULATED",
        "source_path": "SIMULATED-NO-LIVE-SOURCE-READ",
        "capture_mode": "dry_run_placeholder"
    },
    {
        "relative_path": "SHA256SUMS",
        "artifact_type": "checksum_manifest_placeholder",
        "size_bytes": 0,
        "sha256": "SIMULATED-NOT-CALCULATED",
        "source_path": "SIMULATED-NO-LIVE-SOURCE-READ",
        "capture_mode": "dry_run_placeholder"
    },
    {
        "relative_path": "prechange_files_or_state_snapshot/",
        "artifact_type": "prechange_snapshot_placeholder",
        "size_bytes": 0,
        "sha256": "SIMULATED-NOT-CALCULATED",
        "source_path": "SIMULATED-NO-LIVE-SOURCE-READ",
        "capture_mode": "dry_run_placeholder"
    }
]

artifact = {
  "schema": "spot.backup_artifact_manifest_dry_run.v1",
  "phase": "2.26",
  "created_utc": datetime.now(UTC).strftime("%Y%m%d-%H%M%S"),
  "mode": "dry_run_simulation_only",
  "dry_run_status": "simulated_manifest_no_backup_creation",
  "linked_backup_artifact_manifest_contract": contract_path.name,
  "linked_backup_artifact_manifest_contract_file": str(contract_path),
  "linked_backup_binding_contract": contract.get("linked_backup_binding_contract"),
  "linked_executor_preflight": contract.get("linked_executor_preflight"),
  "linked_plugin_request": contract.get("linked_plugin_request"),
  "linked_action_handoff": contract.get("linked_action_handoff"),
  "linked_action_request": contract.get("linked_action_request"),
  "target": contract.get("target"),
  "plugin_name": contract.get("plugin_name"),
  "action_class": contract.get("action_class"),
  "risk_class": contract.get("risk_class"),
  "simulated_manifest": {
    "schema": "spot.backup_artifact_manifest.simulated.v1",
    "manifest_filename": future.get("manifest_filename", "metadata.json"),
    "checksum_filename": future.get("checksum_filename", "SHA256SUMS"),
    "checksum_algorithm": future.get("allowed_checksum_algorithm", "sha256"),
    "checksum_mode": "simulated_not_calculated",
    "backup_artifact_path": "/mnt/collective/backups/<target>/<service>/<timestamp>/",
    "artifact_inventory": synthetic_inventory,
    "verification_result": "not_verified_dry_run_only",
    "rollback_authority": future.get("rollback_authority"),
    "restore_without_recorded_artifact_allowed": future.get("restore_without_recorded_artifact_allowed"),
    "mutation_allowed": False,
    "execution_allowed": False
  },
  "source_contract_requirements_reflected": {
    "required_manifest_fields_present_in_plan": True,
    "required_artifact_inventory_fields_present_in_plan": True,
    "required_verification_checks_reflected_in_plan": True,
    "manifest_required_before_backup_binding": future.get("manifest_required_before_backup_binding"),
    "backup_delete_allowed": future.get("backup_delete_allowed"),
    "backup_overwrite_allowed": future.get("backup_overwrite_allowed")
  },
  "phase_2_26_dry_run_gate": {
    "dry_run_only": True,
    "simulated_manifest_only": True,
    "live_source_files_read": False,
    "live_source_files_hashed": False,
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
    "reason": "phase_2_26_backup_artifact_manifest_dry_run_only_no_live_backup_creation"
  },
  "notes": [
    "This artifact simulates future backup artifact manifest generation only.",
    "This artifact does not read live source files.",
    "This artifact does not hash live source files.",
    "This artifact does not create metadata.json in a backup directory.",
    "This artifact does not create SHA256SUMS in a backup directory.",
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
  file="$(resolve_dry_run_file "${1:-}")"

  assert_eq "$(json_get "$file" schema)" "spot.backup_artifact_manifest_dry_run.v1" "dry-run schema"
  assert_eq "$(json_get "$file" phase)" "2.26" "dry-run phase"
  assert_eq "$(json_get "$file" mode)" "dry_run_simulation_only" "dry-run mode"
  assert_eq "$(json_get "$file" dry_run_status)" "simulated_manifest_no_backup_creation" "dry-run status"

  assert_eq "$(json_get "$file" simulated_manifest.schema)" "spot.backup_artifact_manifest.simulated.v1" "simulated manifest schema"
  assert_eq "$(json_get "$file" simulated_manifest.manifest_filename)" "metadata.json" "manifest filename"
  assert_eq "$(json_get "$file" simulated_manifest.checksum_filename)" "SHA256SUMS" "checksum filename"
  assert_eq "$(json_get "$file" simulated_manifest.checksum_algorithm)" "sha256" "checksum algorithm"
  assert_eq "$(json_get "$file" simulated_manifest.checksum_mode)" "simulated_not_calculated" "checksum mode"
  assert_eq "$(json_get "$file" simulated_manifest.verification_result)" "not_verified_dry_run_only" "verification result"
  assert_eq "$(json_get "$file" simulated_manifest.rollback_authority)" "recorded_prechange_backup_only" "rollback authority"
  assert_false "$(json_get "$file" simulated_manifest.restore_without_recorded_artifact_allowed)" "restore_without_recorded_artifact_allowed"
  assert_false "$(json_get "$file" simulated_manifest.mutation_allowed)" "simulated manifest mutation_allowed"
  assert_false "$(json_get "$file" simulated_manifest.execution_allowed)" "simulated manifest execution_allowed"

  assert_true "$(json_get "$file" source_contract_requirements_reflected.required_manifest_fields_present_in_plan)" "required_manifest_fields_present_in_plan"
  assert_true "$(json_get "$file" source_contract_requirements_reflected.required_artifact_inventory_fields_present_in_plan)" "required_artifact_inventory_fields_present_in_plan"
  assert_true "$(json_get "$file" source_contract_requirements_reflected.required_verification_checks_reflected_in_plan)" "required_verification_checks_reflected_in_plan"
  assert_true "$(json_get "$file" source_contract_requirements_reflected.manifest_required_before_backup_binding)" "manifest_required_before_backup_binding"
  assert_false "$(json_get "$file" source_contract_requirements_reflected.backup_delete_allowed)" "backup_delete_allowed"
  assert_false "$(json_get "$file" source_contract_requirements_reflected.backup_overwrite_allowed)" "backup_overwrite_allowed"

  assert_true "$(json_get "$file" phase_2_26_dry_run_gate.dry_run_only)" "dry_run_only"
  assert_true "$(json_get "$file" phase_2_26_dry_run_gate.simulated_manifest_only)" "simulated_manifest_only"
  assert_false "$(json_get "$file" phase_2_26_dry_run_gate.live_source_files_read)" "live_source_files_read"
  assert_false "$(json_get "$file" phase_2_26_dry_run_gate.live_source_files_hashed)" "live_source_files_hashed"
  assert_false "$(json_get "$file" phase_2_26_dry_run_gate.backup_manifest_created)" "backup_manifest_created"
  assert_false "$(json_get "$file" phase_2_26_dry_run_gate.backup_artifact_created)" "backup_artifact_created"
  assert_false "$(json_get "$file" phase_2_26_dry_run_gate.checksum_generated)" "checksum_generated"
  assert_false "$(json_get "$file" phase_2_26_dry_run_gate.backup_creation_allowed)" "backup_creation_allowed"
  assert_false "$(json_get "$file" phase_2_26_dry_run_gate.backup_binding_active)" "backup_binding_active"
  assert_false "$(json_get "$file" phase_2_26_dry_run_gate.backup_verified)" "backup_verified"
  assert_false "$(json_get "$file" phase_2_26_dry_run_gate.execution_allowed)" "execution_allowed"
  assert_false "$(json_get "$file" phase_2_26_dry_run_gate.mutation_allowed)" "mutation_allowed"
  assert_false "$(json_get "$file" phase_2_26_dry_run_gate.mutation_performed)" "mutation_performed"
  assert_false "$(json_get "$file" phase_2_26_dry_run_gate.executor_dispatch_allowed)" "executor_dispatch_allowed"
  assert_false "$(json_get "$file" phase_2_26_dry_run_gate.service_restart_allowed)" "service_restart_allowed"
  assert_false "$(json_get "$file" phase_2_26_dry_run_gate.config_write_allowed)" "config_write_allowed"
  assert_false "$(json_get "$file" phase_2_26_dry_run_gate.network_mutation_allowed)" "network_mutation_allowed"

  assert_true "$(json_get "$file" result.ok)" "result ok"
  assert_true "$(json_get "$file" result.blocked)" "result blocked"

  echo "OK: backup artifact manifest dry-run verified: $file"
}

cmd_show() {
  local file
  file="$(resolve_dry_run_file "${1:-}")"
  cat "$file"
}

cmd_list() {
  local count="${1:-20}"
  mkdir -p "$DRY_RUN_DIR"
  find "$DRY_RUN_DIR" -maxdepth 1 -type f -name 'BACKUP-ARTIFACT-MANIFEST-DRY-RUN-*.json' -printf '%T@ %p\n' \
    | sort -nr \
    | head -n "$count" \
    | cut -d' ' -f2-
}

main() {
  local cmd="${1:-}"
  shift || true

  case "$cmd" in
    create) cmd_create "$@" ;;
    verify) cmd_verify "$@" ;;
    show) cmd_show "$@" ;;
    list) cmd_list "$@" ;;
    -h|--help|help|"") usage ;;
    *) echo "ERROR: unknown command: $cmd" >&2; usage >&2; exit 2 ;;
  esac
}

main "$@"
