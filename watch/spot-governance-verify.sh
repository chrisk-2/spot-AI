#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="${BASE_DIR:-/home/ogre/spot-stack/watch}"
TASK_DIR="${TASK_DIR:-${BASE_DIR}/tasks/pending}"
JOURNAL_FILE="${JOURNAL_FILE:-${BASE_DIR}/contracts/executor-journal/index.jsonl}"
LEDGER_FILE="${LEDGER_FILE:-${BASE_DIR}/contracts/approval-ledger/index.jsonl}"
TASK_SCRIPT="${TASK_SCRIPT:-${BASE_DIR}/spot-task.sh}"
JOURNAL_SCRIPT="${JOURNAL_SCRIPT:-${BASE_DIR}/spot-executor-journal.sh}"
LEDGER_SCRIPT="${LEDGER_SCRIPT:-${BASE_DIR}/spot-approval-ledger.sh}"

failures=0

fail() {
  echo "FAIL: $*"
  failures=$((failures + 1))
}

need() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "ERROR: required command missing: $1" >&2
    exit 2
  }
}

need jq

[[ -x "$TASK_SCRIPT" ]] || fail "missing executable: $TASK_SCRIPT"
[[ -x "$JOURNAL_SCRIPT" ]] || fail "missing executable: $JOURNAL_SCRIPT"
[[ -x "$LEDGER_SCRIPT" ]] || fail "missing executable: $LEDGER_SCRIPT"
[[ -f "$JOURNAL_FILE" ]] || fail "missing journal: $JOURNAL_FILE"
[[ -f "$LEDGER_FILE" ]] || fail "missing approval ledger: $LEDGER_FILE"

if [[ "$failures" -eq 0 ]]; then
  "$JOURNAL_SCRIPT" verify >/dev/null || fail "executor journal verification failed"
  "$LEDGER_SCRIPT" verify >/dev/null || fail "approval ledger verification failed"
fi

while IFS= read -r task_file; do
  task_id="$(jq -r '.task_id' "$task_file")"
  approval_status="$(jq -r '.approval_status' "$task_file")"

  "$TASK_SCRIPT" verify "$task_file" >/dev/null || fail "task verify failed: $task_id"
  "$TASK_SCRIPT" approval-guard "$task_file" >/dev/null || fail "approval guard failed: $task_id"

  for field in execution_allowed mutation_allowed network_mutation_allowed service_restart_allowed; do
    [[ "$(jq -r ".${field}" "$task_file")" == "false" ]] || fail "$task_id has ${field}=true"
  done

  [[ "$(jq -r '.mode' "$task_file")" == "proposal_only" ]] || fail "$task_id mode not proposal_only"
  [[ "$(jq -r '.risk_class' "$task_file")" == "read_only" ]] || fail "$task_id risk_class not read_only"
  [[ "$(jq -r '.requires_spot_core_apply' "$task_file")" == "true" ]] || fail "$task_id requires_spot_core_apply not true"

  if [[ "$approval_status" == "approved" ]]; then
    grep -q "\"task_id\":\"${task_id}\"" "$LEDGER_FILE" || fail "$task_id approved but missing ledger entry"
    grep -q '"event_type":"task_approved"' "$JOURNAL_FILE" || fail "$task_id approved but missing journal approval event"
  fi
done < <(find "$TASK_DIR" -maxdepth 1 -type f -name '*.json' | sort)

while IFS= read -r task_id; do
  [[ -f "${TASK_DIR}/${task_id}.json" ]] || fail "ledger references missing task: $task_id"
done < <(jq -r '.task_id' "$LEDGER_FILE" | sort -u)

if [[ "$failures" -eq 0 ]]; then
  jq -n \
    --arg task_dir "$TASK_DIR" \
    --arg journal_file "$JOURNAL_FILE" \
    --arg ledger_file "$LEDGER_FILE" \
    '{
      ok: true,
      verified: true,
      governance_state: "consistent",
      policy_state: "proposal_only_locked",
      task_dir: $task_dir,
      journal_file: $journal_file,
      ledger_file: $ledger_file,
      mutation_performed: false,
      execution_performed: false
    }'
  exit 0
fi

echo "RESULT: FAIL failures=${failures}" >&2
exit 1
