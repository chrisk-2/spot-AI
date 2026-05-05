#!/usr/bin/env bash
set -Eeuo pipefail

BASE_DIR="${BASE_DIR:-/home/ogre/spot-stack/watch}"
PREFLIGHT_SCRIPT="${PREFLIGHT_SCRIPT:-${BASE_DIR}/spot-executor-preflight.sh}"
SOURCE_REQUEST="${SOURCE_REQUEST:-${BASE_DIR}/plugin-requests/PLUGIN-REQUEST-20260504-164220-read_only_status_probe-ACTION-HANDOFF-20260504-160158-ACTION-20260504-160153-read_only_diagnostic-spot-core.json}"
TEST_DIR="${TEST_DIR:-${BASE_DIR}/executor-preflight-failure-tests}"

usage() {
  cat <<'USAGE'
Usage:
  spot-executor-preflight-failure-test.sh run

Phase 2.16 only:
- creates temporary malformed plugin request artifacts
- verifies executor preflight rejects unsafe inputs
- performs no mutation, no execution, no service restart, no config write, no network change, and no backup binding
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
  local expr="$2"
  local out="${TEST_DIR}/${name}.json"

  python3 - "$SOURCE_REQUEST" "$out" "$expr" <<'PY'
import json
import sys
from pathlib import Path

source = Path(sys.argv[1])
out = Path(sys.argv[2])
expr = sys.argv[3]

data = json.loads(source.read_text())

if expr == "plugin_execution_allowed_true":
    data["plugin_execution_allowed"] = True
elif expr == "execution_allowed_true":
    data["execution_allowed"] = True
elif expr == "mutation_allowed_true":
    data["mutation_allowed"] = True
elif expr == "mutation_performed_true":
    data["mutation_performed"] = True
elif expr == "backup_bound_true":
    data["backup_bound"] = True
elif expr == "next_allowed_action_execute":
    data["next_allowed_action"] = "execute"
elif expr == "unknown_plugin":
    data["plugin_name"] = "not_a_registered_plugin"
elif expr == "bad_schema":
    data["schema"] = "spot.plugin_request.bad"
elif expr == "request_status_open":
    data["request_status"] = "review_approved_non_executing"
else:
    raise SystemExit(f"unknown expr: {expr}")

data["plugin_request_id"] = f"NEGATIVE-TEST-{expr}"

out.write_text(json.dumps(data, indent=2) + "\n")
print(out)
PY
}

expect_reject() {
  local name="$1"
  local file="$2"
  local log="${TEST_DIR}/${name}.log"

  set +e
  "$PREFLIGHT_SCRIPT" create "$file" >"$log" 2>&1
  local rc=$?
  set -e

  if [[ "$rc" -eq 0 ]]; then
    echo "FAIL: ${name}: unsafe request was accepted: ${file}" >&2
    echo "--- output ---" >&2
    cat "$log" >&2
    return 1
  fi

  echo "PASS: ${name}: rejected rc=${rc}"
}

cmd_run() {
  need_cmd python3
  need_file "$PREFLIGHT_SCRIPT"
  need_file "$SOURCE_REQUEST"

  mkdir -p "$TEST_DIR"
  rm -f "${TEST_DIR}"/*.json "${TEST_DIR}"/*.log

  local failures=0
  local name file

  local cases=(
    "plugin_execution_allowed_true"
    "execution_allowed_true"
    "mutation_allowed_true"
    "mutation_performed_true"
    "backup_bound_true"
    "next_allowed_action_execute"
    "unknown_plugin"
    "bad_schema"
    "request_status_open"
  )

  echo "EXECUTOR_PREFLIGHT_FAILURE_TEST"
  echo "created_utc: $(stamp)"
  echo "source_request: ${SOURCE_REQUEST}"
  echo "test_dir: ${TEST_DIR}"
  echo

  for name in "${cases[@]}"; do
    file="$(write_variant "$name" "$name")"
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
