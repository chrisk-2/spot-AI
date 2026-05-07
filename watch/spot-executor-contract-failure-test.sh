#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="${BASE_DIR:-/home/ogre/spot-stack/watch}"
VERIFY_SCRIPT="${VERIFY_SCRIPT:-${BASE_DIR}/spot-executor-contract.sh}"
SOURCE_CONTRACT="${SOURCE_CONTRACT:-${BASE_DIR}/contracts/examples/codex-readonly-example.json}"
TEST_DIR="${TEST_DIR:-${BASE_DIR}/contracts/failure-tests}"

usage() {
  cat <<USAGE
Usage:
  spot-executor-contract-failure-test.sh run
USAGE
}

need() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "ERROR: required command missing: $1" >&2
    exit 2
  }
}

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

if case == "missing_task_id":
    data.pop("task_id", None)
elif case == "bad_executor_type":
    data["executor_type"] = "freeform_root_shell"
elif case == "bad_risk_class":
    data["risk_class"] = "reckless"
elif case == "bad_mode":
    data["mode"] = "root_everything"
elif case == "codex_live_write_true":
    data["live_write_allowed"] = True
elif case == "network_mutation_true":
    data["network_mutation_allowed"] = True
elif case == "spot_core_apply_no_rollback":
    data["mode"] = "spot_core_apply"
    data["rollback_required"] = False
    data["validation_required"] = True
    data["requires_spot_core_apply"] = True
elif case == "spot_core_apply_no_validation":
    data["mode"] = "spot_core_apply"
    data["rollback_required"] = True
    data["validation_required"] = False
    data["requires_spot_core_apply"] = True
elif case == "spot_core_apply_no_apply_gate":
    data["mode"] = "spot_core_apply"
    data["rollback_required"] = True
    data["validation_required"] = True
    data["requires_spot_core_apply"] = False
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
  "$VERIFY_SCRIPT" verify "$file" >"$log" 2>&1
  local rc=$?
  set -e

  if [[ "$rc" -eq 0 ]]; then
    echo "FAIL: ${name}: unsafe contract accepted"
    cat "$log"
    return 1
  fi

  echo "PASS: ${name}: rejected rc=${rc}"
}

cmd_run() {
  need python3
  need jq
  [[ -x "$VERIFY_SCRIPT" ]] || { echo "ERROR: verifier not executable: $VERIFY_SCRIPT" >&2; exit 2; }
  [[ -f "$SOURCE_CONTRACT" ]] || { echo "ERROR: source contract missing: $SOURCE_CONTRACT" >&2; exit 2; }

  mkdir -p "$TEST_DIR"
  rm -f "${TEST_DIR}"/*.json "${TEST_DIR}"/*.log

  local cases=(
    missing_task_id
    bad_executor_type
    bad_risk_class
    bad_mode
    codex_live_write_true
    network_mutation_true
    spot_core_apply_no_rollback
    spot_core_apply_no_validation
    spot_core_apply_no_apply_gate
  )

  local failures=0 name file

  echo "EXECUTOR_CONTRACT_FAILURE_TEST"
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
    echo "mutation_performed: false"
    echo "execution_performed: false"
    exit 0
  fi

  echo "RESULT: FAIL"
  echo "failures: ${failures}"
  exit 1
}

case "${1:-run}" in
  run) cmd_run ;;
  -h|--help|help) usage ;;
  *) echo "ERROR: unknown command: ${1:-}" >&2; usage >&2; exit 2 ;;
esac
