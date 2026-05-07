#!/usr/bin/env bash
set -euo pipefail

BASE_DIR="${BASE_DIR:-/home/ogre/spot-stack/watch}"
SCHEMA_FILE="${SCHEMA_FILE:-${BASE_DIR}/policy/executor-contract.schema.json}"

usage() {
  cat <<USAGE
Usage:
  spot-executor-contract.sh verify <contract.json>
USAGE
}

need() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "ERROR: required command missing: $1" >&2
    exit 2
  }
}

cmd_verify() {
  need jq

  local file="${1:-}"
  [[ -n "$file" ]] || { echo "ERROR: contract file required" >&2; exit 2; }
  [[ -f "$file" ]] || { echo "ERROR: contract not found: $file" >&2; exit 2; }
  [[ -f "$SCHEMA_FILE" ]] || { echo "ERROR: schema not found: $SCHEMA_FILE" >&2; exit 2; }

  jq -e . "$file" >/dev/null
  jq -e . "$SCHEMA_FILE" >/dev/null

  local missing
  missing="$(
    jq -r --slurpfile schema "$SCHEMA_FILE" '
      . as $contract
      | $schema[0].required_fields[]
      | . as $field
      | select(($contract | has($field)) | not)
    ' "$file"
  )"

  if [[ -n "$missing" ]]; then
    echo "ERROR: missing required fields:"
    echo "$missing"
    exit 2
  fi

  local executor_type risk_class mode
  executor_type="$(jq -r '.executor_type' "$file")"
  risk_class="$(jq -r '.risk_class' "$file")"
  mode="$(jq -r '.mode' "$file")"

  jq -e --arg v "$executor_type" '.allowed_executor_types | index($v)' "$SCHEMA_FILE" >/dev/null || {
    echo "ERROR: executor_type not allowed: $executor_type" >&2
    exit 2
  }

  jq -e --arg v "$risk_class" '.allowed_risk_classes | index($v)' "$SCHEMA_FILE" >/dev/null || {
    echo "ERROR: risk_class not allowed: $risk_class" >&2
    exit 2
  }

  jq -e --arg v "$mode" '.allowed_modes | index($v)' "$SCHEMA_FILE" >/dev/null || {
    echo "ERROR: mode not allowed: $mode" >&2
    exit 2
  }

  if [[ "$executor_type" == "codex" ]]; then
    [[ "$(jq -r '.live_write_allowed' "$file")" == "false" ]] || {
      echo "ERROR: Codex direct live_write_allowed must be false" >&2
      exit 2
    }
  fi

  if [[ "$(jq -r '.network_mutation_allowed' "$file")" != "false" ]]; then
    echo "ERROR: network_mutation_allowed must be false" >&2
    exit 2
  fi

  if [[ "$mode" == "spot_core_apply" ]]; then
    [[ "$(jq -r '.rollback_required' "$file")" == "true" ]] || {
      echo "ERROR: spot_core_apply requires rollback_required=true" >&2
      exit 2
    }
    [[ "$(jq -r '.validation_required' "$file")" == "true" ]] || {
      echo "ERROR: spot_core_apply requires validation_required=true" >&2
      exit 2
    }
    [[ "$(jq -r '.requires_spot_core_apply' "$file")" == "true" ]] || {
      echo "ERROR: spot_core_apply requires requires_spot_core_apply=true" >&2
      exit 2
    }
  fi

  jq -n --arg file "$file" --arg executor_type "$executor_type" --arg risk_class "$risk_class" --arg mode "$mode" '{
    ok: true,
    verified: true,
    file: $file,
    executor_type: $executor_type,
    risk_class: $risk_class,
    mode: $mode,
    mutation_performed: false,
    execution_performed: false
  }'
}

case "${1:-}" in
  verify) shift; cmd_verify "$@" ;;
  -h|--help|help|"") usage ;;
  *) echo "ERROR: unknown command: ${1:-}" >&2; usage >&2; exit 2 ;;
esac
