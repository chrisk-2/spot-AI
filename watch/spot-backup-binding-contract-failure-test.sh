#!/usr/bin/env bash
set -Eeuo pipefail

BASE_DIR="${BASE_DIR:-/home/ogre/spot-stack/watch}"
CONTRACT_SCRIPT="${CONTRACT_SCRIPT:-${BASE_DIR}/spot-backup-binding-contract.sh}"
SOURCE_CONTRACT="${SOURCE_CONTRACT:-$(find "${BASE_DIR}/backup-binding-contracts" -maxdepth 1 -type f -name 'BACKUP-BINDING-CONTRACT-*.json' | sort | tail -n 1)}"
TEST_DIR="${TEST_DIR:-${BASE_DIR}/backup-binding-contract-failure-tests}"

usage() {
  cat <<'USAGE'
Usage:
  spot-backup-binding-contract-failure-test.sh run

Phase 2.20 only:
- creates malformed backup-binding contract artifacts
- verifies contract verifier rejects unsafe design variants
- performs no backup creation, no live backup binding, no execution, and no mutation
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

  python3 - "$SOURCE_CONTRACT" "$out" "$name" <<'PY'
import json
import sys
from pathlib import Path

source = Path(sys.argv[1])
out = Path(sys.argv[2])
case = sys.argv[3]
data = json.loads(source.read_text())

gate = data.setdefault("phase_2_18_design_gate", {})
future = data.setdefault("future_backup_contract", {})
result = data.setdefault("result", {})

if case == "bad_schema":
    data["schema"] = "spot.backup_binding_contract.bad"
elif case == "bad_phase":
    data["phase"] = "2.99"
elif case == "live_mode":
    data["mode"] = "live_binding"
elif case == "bound_status":
    data["contract_status"] = "backup_bound"
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
elif case == "backup_delete_allowed_true":
    future["backup_delete_allowed"] = True
elif case == "backup_overwrite_allowed_true":
    future["backup_overwrite_allowed"] = True
elif case == "bad_rollback_authority":
    future["rollback_authority"] = "invented_runtime_state"
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
  "$CONTRACT_SCRIPT" verify "$file" >"$log" 2>&1
  local rc=$?
  set -e

  if [[ "$rc" -eq 0 ]]; then
    echo "FAIL: ${name}: unsafe contract was accepted: ${file}" >&2
    echo "--- output ---" >&2
    cat "$log" >&2
    return 1
  fi

  echo "PASS: ${name}: rejected rc=${rc}"
}

cmd_run() {
  need_cmd python3
  need_file "$CONTRACT_SCRIPT"
  need_file "$SOURCE_CONTRACT"

  mkdir -p "$TEST_DIR"
  rm -f "${TEST_DIR}"/*.json "${TEST_DIR}"/*.log

  local cases=(
    "bad_schema"
    "bad_phase"
    "live_mode"
    "bound_status"
    "backup_creation_allowed_true"
    "backup_binding_active_true"
    "backup_verified_true"
    "execution_allowed_true"
    "mutation_allowed_true"
    "mutation_performed_true"
    "executor_dispatch_allowed_true"
    "backup_delete_allowed_true"
    "backup_overwrite_allowed_true"
    "bad_rollback_authority"
    "result_not_blocked"
  )

  local failures=0
  local name file

  echo "BACKUP_BINDING_CONTRACT_FAILURE_TEST"
  echo "created_utc: $(stamp)"
  echo "source_contract: ${SOURCE_CONTRACT}"
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
