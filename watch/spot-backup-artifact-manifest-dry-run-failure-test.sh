#!/usr/bin/env bash
set -Eeuo pipefail

BASE_DIR="${BASE_DIR:-/home/ogre/spot-stack/watch}"
DRY_RUN_SCRIPT="${DRY_RUN_SCRIPT:-${BASE_DIR}/spot-backup-artifact-manifest-dry-run.sh}"
SOURCE_DRY_RUN="${SOURCE_DRY_RUN:-$(find "${BASE_DIR}/backup-artifact-manifest-dry-runs" -maxdepth 1 -type f -name 'BACKUP-ARTIFACT-MANIFEST-DRY-RUN-*.json' | sort | tail -n 1)}"
TEST_DIR="${TEST_DIR:-${BASE_DIR}/backup-artifact-manifest-dry-run-failure-tests}"

usage() {
  cat <<'USAGE'
Usage:
  spot-backup-artifact-manifest-dry-run-failure-test.sh run

Phase 2.28 only:
- creates malformed backup artifact manifest dry-run artifacts
- verifies dry-run verifier rejects unsafe variants
- performs no live source file reads, no live hashing, no backup creation, no binding, no execution, and no mutation
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

write_variant() {
  local name="$1"
  local out="${TEST_DIR}/${name}.json"

  python3 - "$SOURCE_DRY_RUN" "$out" "$name" <<'PY'
import json
import sys
from pathlib import Path

source = Path(sys.argv[1])
out = Path(sys.argv[2])
case = sys.argv[3]
data = json.loads(source.read_text())

gate = data.setdefault("phase_2_26_dry_run_gate", {})
sim = data.setdefault("simulated_manifest", {})
result = data.setdefault("result", {})

if case == "bad_schema":
    data["schema"] = "spot.backup_artifact_manifest_dry_run.bad"
elif case == "bad_phase":
    data["phase"] = "2.99"
elif case == "live_mode":
    data["mode"] = "live_manifest_generation"
elif case == "bad_status":
    data["dry_run_status"] = "manifest_created"
elif case == "bad_simulated_manifest_schema":
    sim["schema"] = "spot.backup_artifact_manifest.live.v1"
elif case == "bad_manifest_filename":
    sim["manifest_filename"] = "manifest.txt"
elif case == "bad_checksum_filename":
    sim["checksum_filename"] = "checksums.md5"
elif case == "bad_checksum_algorithm":
    sim["checksum_algorithm"] = "md5"
elif case == "checksum_mode_calculated":
    sim["checksum_mode"] = "calculated"
elif case == "verification_result_verified":
    sim["verification_result"] = "verified"
elif case == "bad_rollback_authority":
    sim["rollback_authority"] = "runtime_guess"
elif case == "restore_without_recorded_artifact_allowed_true":
    sim["restore_without_recorded_artifact_allowed"] = True
elif case == "simulated_mutation_allowed_true":
    sim["mutation_allowed"] = True
elif case == "simulated_execution_allowed_true":
    sim["execution_allowed"] = True
elif case == "live_source_files_read_true":
    gate["live_source_files_read"] = True
elif case == "live_source_files_hashed_true":
    gate["live_source_files_hashed"] = True
elif case == "backup_manifest_created_true":
    gate["backup_manifest_created"] = True
elif case == "backup_artifact_created_true":
    gate["backup_artifact_created"] = True
elif case == "checksum_generated_true":
    gate["checksum_generated"] = True
elif case == "backup_creation_allowed_true":
    gate["backup_creation_allowed"] = True
elif case == "backup_binding_active_true":
    gate["backup_binding_active"] = True
elif case == "backup_verified_true":
    gate["backup_verified"] = True
elif case == "execution_allowed_true":
    gate["execution_allowed"] = True
elif case == "mutation_allowed_true":
    gate["mutation_allowed"] = True
elif case == "mutation_performed_true":
    gate["mutation_performed"] = True
elif case == "executor_dispatch_allowed_true":
    gate["executor_dispatch_allowed"] = True
elif case == "service_restart_allowed_true":
    gate["service_restart_allowed"] = True
elif case == "config_write_allowed_true":
    gate["config_write_allowed"] = True
elif case == "network_mutation_allowed_true":
    gate["network_mutation_allowed"] = True
elif case == "result_not_blocked":
    result["blocked"] = False
else:
    raise SystemExit(f"unknown case: {case}")

out.write_text(json.dumps(data, indent=2) + "\n")
print(out)
PY
}

expect_reject() {
  local name="$1"
  local file="$2"
  local log="${TEST_DIR}/${name}.log"

  set +e
  "$DRY_RUN_SCRIPT" verify "$file" >"$log" 2>&1
  local rc=$?
  set -e

  if [[ "$rc" -eq 0 ]]; then
    echo "FAIL: ${name}: unsafe dry-run was accepted: ${file}" >&2
    echo "--- output ---" >&2
    cat "$log" >&2
    return 1
  fi

  echo "PASS: ${name}: rejected rc=${rc}"
}

cmd_run() {
  need_cmd python3
  need_file "$DRY_RUN_SCRIPT"
  need_file "$SOURCE_DRY_RUN"

  mkdir -p "$TEST_DIR"
  rm -f "${TEST_DIR}"/*.json "${TEST_DIR}"/*.log

  local cases=(
    "bad_schema"
    "bad_phase"
    "live_mode"
    "bad_status"
    "bad_simulated_manifest_schema"
    "bad_manifest_filename"
    "bad_checksum_filename"
    "bad_checksum_algorithm"
    "checksum_mode_calculated"
    "verification_result_verified"
    "bad_rollback_authority"
    "restore_without_recorded_artifact_allowed_true"
    "simulated_mutation_allowed_true"
    "simulated_execution_allowed_true"
    "live_source_files_read_true"
    "live_source_files_hashed_true"
    "backup_manifest_created_true"
    "backup_artifact_created_true"
    "checksum_generated_true"
    "backup_creation_allowed_true"
    "backup_binding_active_true"
    "backup_verified_true"
    "execution_allowed_true"
    "mutation_allowed_true"
    "mutation_performed_true"
    "executor_dispatch_allowed_true"
    "service_restart_allowed_true"
    "config_write_allowed_true"
    "network_mutation_allowed_true"
    "result_not_blocked"
  )

  local failures=0
  local name file

  echo "BACKUP_ARTIFACT_MANIFEST_DRY_RUN_FAILURE_TEST"
  echo "created_utc: $(stamp)"
  echo "source_dry_run: ${SOURCE_DRY_RUN}"
  echo "test_dir: ${TEST_DIR}"
  echo

  for name in "${cases[@]}"; do
    file="$(write_variant "$name")"
    if ! expect_reject "$name" "$file"; then
      failures=$((failures + 1))
    fi
  done

  echo
  if [[ "$failures" -eq 0 ]]; then
    echo "RESULT: PASS"
    echo "rejected_cases: ${#cases[@]}"
    echo "live_source_files_read: false"
    echo "live_source_files_hashed: false"
    echo "backup_manifest_created: false"
    echo "backup_artifact_created: false"
    echo "checksum_generated: false"
    echo "backup_creation_performed: false"
    echo "backup_binding_performed: false"
    echo "mutation_performed: false"
    echo "execution_performed: false"
    exit 0
  fi

  echo "RESULT: FAIL"
  echo "failures: ${failures}"
  exit 1
}

main() {
  local cmd="${1:-run}"
  shift || true

  case "$cmd" in
    run) cmd_run "$@" ;;
    -h|--help|help) usage ;;
    *) echo "ERROR: unknown command: $cmd" >&2; usage >&2; exit 2 ;;
  esac
}

main "$@"
