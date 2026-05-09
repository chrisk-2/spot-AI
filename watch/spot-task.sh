#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="${BASE_DIR:-/home/ogre/spot-stack/watch}"

TASK_DIR="${TASK_DIR:-${BASE_DIR}/tasks}"
PENDING_DIR="${PENDING_DIR:-${TASK_DIR}/pending}"

SCHEMA_FILE="${SCHEMA_FILE:-${BASE_DIR}/policy/task.schema.json}"

EXECUTOR_CONTRACT_SCRIPT="${EXECUTOR_CONTRACT_SCRIPT:-${BASE_DIR}/spot-executor-contract.sh}"
EXECUTOR_JOURNAL_SCRIPT="${EXECUTOR_JOURNAL_SCRIPT:-${BASE_DIR}/spot-executor-journal.sh}"

usage() {
  cat <<USAGE
Usage:
  spot-task.sh create <task.json>
  spot-task.sh list [count]
  spot-task.sh show <task-id|file>
  spot-task.sh verify <task-id|file>
  spot-task.sh approval-guard <task-id|file>
  spot-task.sh review <task-id|file>
  spot-task.sh approve <task-id|file> <reviewer>
  spot-task.sh revoke-approval <task-id|file>
  spot-task.sh reject <task-id|file>
  spot-task.sh complete <task-id|file>
  spot-task.sh summary
USAGE
}

need() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "ERROR: required command missing: $1" >&2
    exit 2
  }
}

init_dirs() {
  mkdir -p "$PENDING_DIR"
}

resolve_task_file() {
  local input="${1:-}"

  [[ -n "$input" ]] || {
    echo "ERROR: task id or file required" >&2
    exit 2
  }

  if [[ -f "$input" ]]; then
    echo "$input"
    return
  fi

  local candidate="${PENDING_DIR}/${input}.json"

  [[ -f "$candidate" ]] || {
    echo "ERROR: task not found: $input" >&2
    exit 2
  }

  echo "$candidate"
}

verify_required_fields() {
  local file="$1"

  local missing

  missing="$(
    jq -r --slurpfile schema "$SCHEMA_FILE" '
      . as $task
      | $schema[0].required_fields[]
      | . as $field
      | select(($task | has($field)) | not)
    ' "$file"
  )"

  if [[ -n "$missing" ]]; then
    echo "ERROR: missing required fields:"
    echo "$missing"
    exit 2
  fi
}

verify_allowed_value() {
  local file="$1"
  local field="$2"
  local schema_key="$3"

  local value

  value="$(jq -r ".${field}" "$file")"

  jq -e --arg v "$value" ".${schema_key} | index(\$v)" "$SCHEMA_FILE" >/dev/null || {
    echo "ERROR: invalid ${field}: ${value}" >&2
    exit 2
  }
}

verify_false_flag() {
  local file="$1"
  local field="$2"

  if [[ "$(jq -r ".${field}" "$file")" != "false" ]]; then
    echo "ERROR: ${field} must be false" >&2
    exit 2
  fi
}

cmd_verify() {
  need jq

  local input="${1:-}"
  local file

  file="$(resolve_task_file "$input")"

  [[ -f "$SCHEMA_FILE" ]] || {
    echo "ERROR: schema not found: $SCHEMA_FILE" >&2
    exit 2
  }

  jq -e . "$file" >/dev/null
  jq -e . "$SCHEMA_FILE" >/dev/null

  verify_required_fields "$file"

  verify_allowed_value "$file" "executor_type" "allowed_executor_types"
  verify_allowed_value "$file" "mode" "allowed_modes"
  verify_allowed_value "$file" "risk_class" "allowed_risk_classes"
  verify_allowed_value "$file" "status" "allowed_statuses"
  verify_allowed_value "$file" "approval_status" "allowed_approval_statuses"

  verify_false_flag "$file" "mutation_allowed"
  verify_false_flag "$file" "execution_allowed"
  verify_false_flag "$file" "network_mutation_allowed"
  verify_false_flag "$file" "service_restart_allowed"

  local contract_file

  contract_file="$(jq -r '.contract_file' "$file")"

  "$EXECUTOR_CONTRACT_SCRIPT" verify "$contract_file" >/dev/null

  jq -n \
    --arg file "$file" \
    '{
      ok: true,
      verified: true,
      file: $file,
      mutation_performed: false,
      execution_performed: false
    }'
}

cmd_approval_guard() {
  need jq

  local input="${1:-}"
  local file

  file="$(resolve_task_file "$input")"

  cmd_verify "$file" >/dev/null

  local violations

  violations="$(
    jq -r '
      [
        if .execution_allowed != false then "execution_allowed must remain false" else empty end,
        if .mutation_allowed != false then "mutation_allowed must remain false" else empty end,
        if .network_mutation_allowed != false then "network_mutation_allowed must remain false" else empty end,
        if .service_restart_allowed != false then "service_restart_allowed must remain false" else empty end,
        if .mode != "proposal_only" then "mode must remain proposal_only" else empty end,
        if .risk_class != "read_only" then "risk_class must remain read_only" else empty end,
        if .requires_spot_core_apply != true then "requires_spot_core_apply must remain true" else empty end
      ] | .[]
    ' "$file"
  )"

  if [[ -n "$violations" ]]; then
    jq -n \
      --arg file "$file" \
      --arg violations "$violations" \
      '{
        ok: false,
        guard: "approval-state",
        file: $file,
        violations: ($violations | split("\n") | map(select(length > 0)))
      }'
    exit 1
  fi

  jq -n \
    --arg file "$file" \
    --arg approval_status "$(jq -r '.approval_status' "$file")" \
    '{
      ok: true,
      guard: "approval-state",
      file: $file,
      approval_status: $approval_status,
      execution_allowed: false,
      mutation_allowed: false,
      network_mutation_allowed: false,
      service_restart_allowed: false,
      mode: "proposal_only",
      risk_class: "read_only",
      requires_spot_core_apply: true,
      execution_blocked: true,
      mutation_blocked: true,
      policy_state: "proposal_only_locked"
    }'
}

cmd_create() {
  need jq

  local input="${1:-}"

  [[ -n "$input" ]] || {
    echo "ERROR: task file required" >&2
    exit 2
  }

  [[ -f "$input" ]] || {
    echo "ERROR: task file not found: $input" >&2
    exit 2
  }

  init_dirs

  cmd_verify "$input" >/dev/null

  local task_id
  task_id="$(jq -r '.task_id' "$input")"

  local out_file="${PENDING_DIR}/${task_id}.json"

  cp "$input" "$out_file"

  "$EXECUTOR_JOURNAL_SCRIPT" append \
    task_proposed \
    "$(jq -r '.contract_file' "$out_file")" >/dev/null

  jq . "$out_file"
}

cmd_set_status() {
  need jq

  local new_status="${1:-}"
  local event="${2:-}"
  local input="${3:-}"

  [[ -n "$new_status" ]] || { echo "ERROR: status required" >&2; exit 2; }
  [[ -n "$event" ]] || { echo "ERROR: journal event required" >&2; exit 2; }

  local file
  file="$(resolve_task_file "$input")"

  cmd_verify "$file" >/dev/null

  jq --arg status "$new_status" '.status = $status' "$file" > "${file}.tmp"
  mv "${file}.tmp" "$file"

  cmd_verify "$file" >/dev/null

  "$EXECUTOR_JOURNAL_SCRIPT" append \
    "$event" \
    "$(jq -r '.contract_file' "$file")" >/dev/null

  jq . "$file"
}

cmd_set_approval() {
  need jq

  local approval_status="${1:-}"
  local reviewer="${2:-}"
  local event="${3:-}"
  local input="${4:-}"

  [[ -n "$approval_status" ]] || { echo "ERROR: approval status required" >&2; exit 2; }
  [[ -n "$event" ]] || { echo "ERROR: journal event required" >&2; exit 2; }

  local file
  file="$(resolve_task_file "$input")"

  cmd_verify "$file" >/dev/null

  local ts
  ts="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

  jq \
    --arg approval_status "$approval_status" \
    --arg reviewer "$reviewer" \
    --arg ts "$ts" \
    '
      .approval_status = $approval_status
      | .approved_by = (if $reviewer == "" then null else $reviewer end)
      | .approved_ts = (if $reviewer == "" then null else $ts end)
    ' "$file" > "${file}.tmp"

  mv "${file}.tmp" "$file"

  cmd_verify "$file" >/dev/null

  "$EXECUTOR_JOURNAL_SCRIPT" append \
    "$event" \
    "$(jq -r '.contract_file' "$file")" >/dev/null

  if [[ "$approval_status" == "approved" ]]; then
    "${BASE_DIR}/spot-approval-ledger.sh" append \
      "$(jq -r '.task_id' "$file")" \
      "${reviewer:-operator}" \
      approved \
      approved >/dev/null
  fi

  jq . "$file"
}

cmd_review() {
  cmd_set_status reviewed task_reviewed "${1:-}"
}

cmd_approve() {
  local input="${1:-}"
  local reviewer="${2:-}"

  [[ -n "$reviewer" ]] || {
    echo "ERROR: reviewer required" >&2
    exit 2
  }

  cmd_set_approval approved "$reviewer" task_approved "$input"
}

cmd_revoke_approval() {
  cmd_set_approval not_approved "" task_approval_revoked "${1:-}"
}

cmd_reject() {
  cmd_set_status rejected task_rejected "${1:-}"
}

cmd_complete() {
  cmd_set_status completed task_completed "${1:-}"
}

cmd_list() {
  need jq

  init_dirs

  local count="${1:-20}"

  find "$PENDING_DIR" -maxdepth 1 -type f -name '*.json' \
    | sort \
    | tail -n "$count" \
    | xargs -r jq -r '[.task_id,.status,.approval_status,.executor_type,.risk_class] | @tsv' \
    | column -t -s $'\t'
}

cmd_show() {
  need jq

  local file
  file="$(resolve_task_file "${1:-}")"

  jq . "$file"
}

cmd_summary() {
  need jq

  init_dirs

  find "$PENDING_DIR" -maxdepth 1 -type f -name '*.json' -print0 \
    | xargs -0 jq -s '
      {
        ok: true,
        tasks: length,
        by_status: (
          group_by(.status)
          | map({
              status: .[0].status,
              count: length
            })
        ),
        by_approval_status: (
          group_by(.approval_status)
          | map({
              approval_status: .[0].approval_status,
              count: length
            })
        ),
        mutation_performed: false,
        execution_performed: false
      }
    '
}

case "${1:-}" in
  create) shift; cmd_create "$@" ;;
  list) shift; cmd_list "$@" ;;
  show) shift; cmd_show "$@" ;;
  verify) shift; cmd_verify "$@" ;;
  approval-guard) shift; cmd_approval_guard "$@" ;;
  review) shift; cmd_review "$@" ;;
  approve) shift; cmd_approve "$@" ;;
  revoke-approval) shift; cmd_revoke_approval "$@" ;;
  reject) shift; cmd_reject "$@" ;;
  complete) shift; cmd_complete "$@" ;;
  summary) cmd_summary ;;
  -h|--help|help|"") usage ;;
  *)
    echo "ERROR: unknown command: ${1:-}" >&2
    usage >&2
    exit 2
    ;;
esac
