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

cmd_list() {
  need jq

  init_dirs

  local count="${1:-20}"

  find "$PENDING_DIR" -maxdepth 1 -type f -name '*.json' \
    | sort \
    | tail -n "$count" \
    | xargs -r jq -r '[.task_id,.status,.executor_type,.risk_class] | @tsv' \
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
  summary) cmd_summary ;;
  -h|--help|help|"") usage ;;
  *)
    echo "ERROR: unknown command: ${1:-}" >&2
    usage >&2
    exit 2
    ;;
esac
