#!/usr/bin/env bash
set -Eeuo pipefail

BASE_DIR="${BASE_DIR:-/home/ogre/spot-stack/watch}"
VERIFY_SCRIPT="${VERIFY_SCRIPT:-${BASE_DIR}/spot-openai-provider-contract.sh}"
SOURCE_CONTRACT="${SOURCE_CONTRACT:-}"
TEST_DIR="${TEST_DIR:-${BASE_DIR}/openai-provider-contract-failure-tests}"

usage() {
  cat <<'USAGE'
Usage:
  spot-openai-provider-contract-failure-test.sh run

Verifies unsafe OpenAI provider governance contract variants are rejected.
USAGE
}

need_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "ERROR: required command not found: $1" >&2
    exit 2
  }
}

resolve_source_contract() {
  if [[ -n "$SOURCE_CONTRACT" ]]; then
    [[ -f "$SOURCE_CONTRACT" ]] || { echo "ERROR: source contract missing: $SOURCE_CONTRACT" >&2; exit 2; }
    printf '%s' "$SOURCE_CONTRACT"
    return 0
  fi

  local latest
  latest="$(bash "$VERIFY_SCRIPT" list 1 | head -n 1 || true)"
  [[ -n "$latest" && -f "$latest" ]] || { echo "ERROR: no source OpenAI provider contract found; run ${VERIFY_SCRIPT} create first" >&2; exit 2; }
  printf '%s' "$latest"
}

write_variant() {
  local name="$1"
  local source="$2"
  local out="${TEST_DIR}/${name}.json"

  python3 - "$source" "$out" "$name" <<'PY'
import json
import sys
from pathlib import Path

source = Path(sys.argv[1])
out = Path(sys.argv[2])
case = sys.argv[3]
data = json.loads(source.read_text())

if case == "execution_allowed_true":
    data["hard_gates"]["execution_allowed"] = True
elif case == "mutation_allowed_true":
    data["hard_gates"]["mutation_allowed"] = True
elif case == "executor_dispatch_allowed_true":
    data["hard_gates"]["executor_dispatch_allowed"] = True
elif case == "service_restart_allowed_true":
    data["hard_gates"]["service_restart_allowed"] = True
elif case == "config_write_allowed_true":
    data["hard_gates"]["config_write_allowed"] = True
elif case == "network_mutation_allowed_true":
    data["hard_gates"]["network_mutation_allowed"] = True
elif case == "backup_creation_allowed_true":
    data["hard_gates"]["backup_creation_allowed"] = True
elif case == "backup_binding_active_true":
    data["hard_gates"]["backup_binding_active"] = True
elif case == "unrestricted_shell_allowed_true":
    data["hard_gates"]["unrestricted_shell_allowed"] = True
elif case == "direct_apply_allowed_true":
    data["hard_gates"]["direct_apply_allowed"] = True
elif case == "direct_admin_write_allowed_true":
    data["hard_gates"]["direct_admin_write_allowed"] = True
elif case == "direct_filesystem_mutation_allowed_true":
    data["hard_gates"]["direct_filesystem_mutation_allowed"] = True
elif case == "provider_not_openai":
    data["provider"] = "unknown_provider"
elif case == "mode_not_external_ai_governance":
    data["mode"] = "direct_executor"
elif case == "tool_authority_not_proposal_review":
    data["tool_authority"] = "direct_apply"
elif case == "missing_policy_review_scope":
    data["review_scope"] = [x for x in data.get("review_scope", []) if x != "policy_review"]
elif case == "spot_core_not_apply_authority":
    data["authority"]["spot_core_is_apply_authority"] = False
elif case == "operator_approval_not_required":
    data["authority"]["operator_approval_required_for_apply"] = False
elif case == "result_blocked_false":
    data["result"]["blocked"] = False
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
  bash "$VERIFY_SCRIPT" verify "$file" >"$log" 2>&1
  local rc=$?
  set -e

  if [[ "$rc" -eq 0 ]]; then
    echo "FAIL: ${name}: unsafe OpenAI provider contract accepted"
    cat "$log"
    return 1
  fi

  echo "PASS: ${name}: rejected rc=${rc}"
}

cmd_run() {
  need_cmd python3
  need_cmd jq
  [[ -f "$VERIFY_SCRIPT" ]] || { echo "ERROR: verifier missing: $VERIFY_SCRIPT" >&2; exit 2; }

  mkdir -p "$TEST_DIR"
  rm -f "${TEST_DIR}"/*.json "${TEST_DIR}"/*.log

  local source
  source="$(resolve_source_contract)"

  local cases=(
    execution_allowed_true
    mutation_allowed_true
    executor_dispatch_allowed_true
    service_restart_allowed_true
    config_write_allowed_true
    network_mutation_allowed_true
    backup_creation_allowed_true
    backup_binding_active_true
    unrestricted_shell_allowed_true
    direct_apply_allowed_true
    direct_admin_write_allowed_true
    direct_filesystem_mutation_allowed_true
    provider_not_openai
    mode_not_external_ai_governance
    tool_authority_not_proposal_review
    missing_policy_review_scope
    spot_core_not_apply_authority
    operator_approval_not_required
    result_blocked_false
  )

  local failures=0 name file

  echo "OPENAI_PROVIDER_CONTRACT_FAILURE_TEST"
  echo "source_contract: ${source}"
  echo "test_dir: ${TEST_DIR}"
  echo

  for name in "${cases[@]}"; do
    file="$(write_variant "$name" "$source")"
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
