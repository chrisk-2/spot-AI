#!/usr/bin/env bash
set -Eeuo pipefail

BASE_DIR="${BASE_DIR:-/home/ogre/spot-stack/watch}"
STATE_DIR="${STATE_DIR:-${BASE_DIR}/state}"
CHECKPOINT_DIR="${CHECKPOINT_DIR:-${BASE_DIR}/readiness-gate-checkpoints}"

EXECUTOR_PREFLIGHT_SCRIPT="${EXECUTOR_PREFLIGHT_SCRIPT:-${BASE_DIR}/spot-executor-preflight.sh}"
BACKUP_BINDING_CONTRACT_SCRIPT="${BACKUP_BINDING_CONTRACT_SCRIPT:-${BASE_DIR}/spot-backup-binding-contract.sh}"
MANIFEST_CONTRACT_SCRIPT="${MANIFEST_CONTRACT_SCRIPT:-${BASE_DIR}/spot-backup-artifact-manifest-contract.sh}"
MANIFEST_DRY_RUN_SCRIPT="${MANIFEST_DRY_RUN_SCRIPT:-${BASE_DIR}/spot-backup-artifact-manifest-dry-run.sh}"
CODEX_PROPOSAL_CONTRACT_SCRIPT="${CODEX_PROPOSAL_CONTRACT_SCRIPT:-${BASE_DIR}/spot-codex-proposal-contract.sh}"
OPENAI_PROVIDER_CONTRACT_SCRIPT="${OPENAI_PROVIDER_CONTRACT_SCRIPT:-${BASE_DIR}/spot-openai-provider-contract.sh}"

EXECUTOR_FAILURE_SCRIPT="${EXECUTOR_FAILURE_SCRIPT:-${BASE_DIR}/spot-executor-preflight-failure-test.sh}"
BACKUP_BINDING_FAILURE_SCRIPT="${BACKUP_BINDING_FAILURE_SCRIPT:-${BASE_DIR}/spot-backup-binding-contract-failure-test.sh}"
MANIFEST_CONTRACT_FAILURE_SCRIPT="${MANIFEST_CONTRACT_FAILURE_SCRIPT:-${BASE_DIR}/spot-backup-artifact-manifest-contract-failure-test.sh}"
MANIFEST_DRY_RUN_FAILURE_SCRIPT="${MANIFEST_DRY_RUN_FAILURE_SCRIPT:-${BASE_DIR}/spot-backup-artifact-manifest-dry-run-failure-test.sh}"
CODEX_PROPOSAL_FAILURE_SCRIPT="${CODEX_PROPOSAL_FAILURE_SCRIPT:-${BASE_DIR}/spot-codex-proposal-contract-failure-test.sh}"
OPENAI_PROVIDER_FAILURE_SCRIPT="${OPENAI_PROVIDER_FAILURE_SCRIPT:-${BASE_DIR}/spot-openai-provider-contract-failure-test.sh}"

usage() {
  cat <<'USAGE'
Usage:
  spot-readiness-gate-checkpoint.sh create
  spot-readiness-gate-checkpoint.sh verify <checkpoint-id-or-file>
  spot-readiness-gate-checkpoint.sh show <checkpoint-id-or-file>
  spot-readiness-gate-checkpoint.sh list [count]

Phase 2.29 only:
- aggregates existing non-mutating proof lanes
- verifies summaries and failure-path harnesses
- produces readiness checkpoint artifacts only
- performs no backup creation, no backup binding, no live source reads, no live hashing, no mutation, and no executor dispatch
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

resolve_checkpoint_file() {
  local id="${1:-}"
  [[ -n "$id" ]] || { echo "ERROR: readiness checkpoint id/file required" >&2; exit 2; }

  local file="$id"
  [[ -f "$file" ]] || file="${CHECKPOINT_DIR}/${id%.json}.json"
  [[ -f "$file" ]] || file="${CHECKPOINT_DIR}/READINESS-GATE-CHECKPOINT-${id#READINESS-GATE-CHECKPOINT-}.json"

  [[ -f "$file" ]] || {
    echo "ERROR: readiness checkpoint not found: $id" >&2
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

assert_false() { assert_eq "$1" "false" "$2"; }
assert_true() { assert_eq "$1" "true" "$2"; }

cmd_create() {
  need_cmd python3
  need_cmd jq

  need_file "$EXECUTOR_PREFLIGHT_SCRIPT"
  need_file "$BACKUP_BINDING_CONTRACT_SCRIPT"
  need_file "$MANIFEST_CONTRACT_SCRIPT"
  need_file "$MANIFEST_DRY_RUN_SCRIPT"
  need_file "$CODEX_PROPOSAL_CONTRACT_SCRIPT"
  need_file "$OPENAI_PROVIDER_CONTRACT_SCRIPT"

  need_file "$EXECUTOR_FAILURE_SCRIPT"
  need_file "$BACKUP_BINDING_FAILURE_SCRIPT"
  need_file "$MANIFEST_CONTRACT_FAILURE_SCRIPT"
  need_file "$MANIFEST_DRY_RUN_FAILURE_SCRIPT"
  need_file "$CODEX_PROPOSAL_FAILURE_SCRIPT"
  need_file "$OPENAI_PROVIDER_FAILURE_SCRIPT"

  mkdir -p "$CHECKPOINT_DIR" "$STATE_DIR"

  local ts out
  ts="$(stamp)"
  out="${CHECKPOINT_DIR}/READINESS-GATE-CHECKPOINT-${ts}.json"

  local executor_summary backup_binding_summary manifest_contract_summary manifest_dry_run_summary codex_summary openai_summary
  local executor_failure_log backup_binding_failure_log manifest_contract_failure_log manifest_dry_run_failure_log codex_failure_log openai_failure_log

  executor_summary="$(mktemp)"
  backup_binding_summary="$(mktemp)"
  manifest_contract_summary="$(mktemp)"
  manifest_dry_run_summary="$(mktemp)"
  codex_summary="$(mktemp)"
  openai_summary="$(mktemp)"

  executor_failure_log="$(mktemp)"
  backup_binding_failure_log="$(mktemp)"
  manifest_contract_failure_log="$(mktemp)"
  manifest_dry_run_failure_log="$(mktemp)"
  codex_failure_log="$(mktemp)"
  openai_failure_log="$(mktemp)"

  "$EXECUTOR_PREFLIGHT_SCRIPT" summary >"$executor_summary"
  "$BACKUP_BINDING_CONTRACT_SCRIPT" summary >"$backup_binding_summary"
  "$MANIFEST_CONTRACT_SCRIPT" summary >"$manifest_contract_summary"
  "$MANIFEST_DRY_RUN_SCRIPT" summary >"$manifest_dry_run_summary"
  bash "$CODEX_PROPOSAL_CONTRACT_SCRIPT" summary >"$codex_summary"
  bash "$OPENAI_PROVIDER_CONTRACT_SCRIPT" summary >"$openai_summary"

  "$EXECUTOR_FAILURE_SCRIPT" run >"$executor_failure_log"
  "$BACKUP_BINDING_FAILURE_SCRIPT" run >"$backup_binding_failure_log"
  "$MANIFEST_CONTRACT_FAILURE_SCRIPT" run >"$manifest_contract_failure_log"
  "$MANIFEST_DRY_RUN_FAILURE_SCRIPT" run >"$manifest_dry_run_failure_log"
  bash "$CODEX_PROPOSAL_FAILURE_SCRIPT" run >"$codex_failure_log"
  bash "$OPENAI_PROVIDER_FAILURE_SCRIPT" run >"$openai_failure_log"

  python3 - "$out" \
    "$executor_summary" \
    "$backup_binding_summary" \
    "$manifest_contract_summary" \
    "$manifest_dry_run_summary" \
    "$codex_summary" \
    "$openai_summary" \
    "$executor_failure_log" \
    "$backup_binding_failure_log" \
    "$manifest_contract_failure_log" \
    "$manifest_dry_run_failure_log" \
    "$codex_failure_log" \
    "$openai_failure_log" <<'PY'
import json
import sys
from pathlib import Path
from datetime import datetime, UTC

out = Path(sys.argv[1])
executor_summary = json.loads(Path(sys.argv[2]).read_text())
backup_binding_summary = json.loads(Path(sys.argv[3]).read_text())
manifest_contract_summary = json.loads(Path(sys.argv[4]).read_text())
manifest_dry_run_summary = json.loads(Path(sys.argv[5]).read_text())
codex_summary = json.loads(Path(sys.argv[6]).read_text())
openai_summary = json.loads(Path(sys.argv[7]).read_text())

logs = {
    "executor_preflight_failure_validation": Path(sys.argv[8]).read_text(),
    "backup_binding_contract_failure_validation": Path(sys.argv[9]).read_text(),
    "backup_artifact_manifest_contract_failure_validation": Path(sys.argv[10]).read_text(),
    "backup_artifact_manifest_dry_run_failure_validation": Path(sys.argv[11]).read_text(),
    "codex_proposal_contract_failure_validation": Path(sys.argv[12]).read_text(),
    "openai_provider_contract_failure_validation": Path(sys.argv[13]).read_text(),
}

failure_results = {}
for name, text in logs.items():
    failure_results[name] = {
        "pass": "RESULT: PASS" in text,
        "rejected_cases_line": next((line for line in text.splitlines() if line.startswith("rejected_cases:")), ""),
        "mutation_performed_false": "mutation_performed: false" in text,
        "execution_performed_false": "execution_performed: false" in text,
    }

summary_checks = {
    "executor_preflight": {
        "schema": executor_summary.get("schema"),
        "count": executor_summary.get("count"),
        "verified_count": executor_summary.get("verified_count"),
        "invalid_count": executor_summary.get("invalid_count"),
        "clean": executor_summary.get("all_known_preflights_blocked_and_non_mutating") is True,
    },
    "backup_binding_contract": {
        "schema": backup_binding_summary.get("schema"),
        "count": backup_binding_summary.get("count"),
        "verified_count": backup_binding_summary.get("verified_count"),
        "invalid_count": backup_binding_summary.get("invalid_count"),
        "clean": backup_binding_summary.get("all_known_contracts_design_only_blocked_and_non_mutating") is True,
    },
    "backup_artifact_manifest_contract": {
        "schema": manifest_contract_summary.get("schema"),
        "count": manifest_contract_summary.get("count"),
        "verified_count": manifest_contract_summary.get("verified_count"),
        "invalid_count": manifest_contract_summary.get("invalid_count"),
        "clean": manifest_contract_summary.get("all_known_manifest_contracts_design_only_blocked_and_non_mutating") is True,
    },
    "backup_artifact_manifest_dry_run": {
        "schema": manifest_dry_run_summary.get("schema"),
        "count": manifest_dry_run_summary.get("count"),
        "verified_count": manifest_dry_run_summary.get("verified_count"),
        "invalid_count": manifest_dry_run_summary.get("invalid_count"),
        "clean": manifest_dry_run_summary.get("all_known_dry_runs_simulated_only_blocked_and_non_mutating") is True,
    },
    "codex_proposal_contract": {
        "schema": codex_summary.get("schema"),
        "count": codex_summary.get("count"),
        "verified_count": codex_summary.get("verified_count"),
        "invalid_count": codex_summary.get("invalid_count"),
        "clean": codex_summary.get("all_known_codex_proposal_contracts_blocked_and_non_mutating") is True,
    },
    "openai_provider_contract": {
        "schema": openai_summary.get("schema"),
        "count": openai_summary.get("count"),
        "verified_count": openai_summary.get("verified_count"),
        "invalid_count": openai_summary.get("invalid_count"),
        "clean": openai_summary.get("all_known_openai_provider_contracts_blocked_and_non_mutating") is True,
    },
}

all_summaries_clean = all(item["clean"] and item["invalid_count"] == 0 for item in summary_checks.values())
all_failure_harnesses_pass = all(item["pass"] for item in failure_results.values())

artifact = {
    "schema": "spot.readiness_gate_checkpoint.v1",
    "phase": "2.29",
    "created_utc": datetime.now(UTC).strftime("%Y%m%d-%H%M%S"),
    "mode": "checkpoint_only_non_mutating",
    "checkpoint_status": "ready_for_review_not_ready_for_live_execution",
    "summary_checks": summary_checks,
    "failure_results": failure_results,
    "readiness_gate": {
        "all_summaries_clean": all_summaries_clean,
        "all_failure_harnesses_pass": all_failure_harnesses_pass,
        "control_plane_ready_for_live_backup_design_review": all_summaries_clean and all_failure_harnesses_pass,
        "live_backup_creation_allowed": False,
        "live_backup_binding_allowed": False,
        "live_source_file_reads_allowed": False,
        "live_source_file_hashing_allowed": False,
        "checksum_generation_allowed": False,
        "executor_dispatch_allowed": False,
        "execution_allowed": False,
        "mutation_allowed": False,
        "mutation_performed": False,
        "service_restart_allowed": False,
        "config_write_allowed": False,
        "network_mutation_allowed": False,
        "direct_apply_allowed": False,
        "direct_admin_write_allowed": False,
        "direct_filesystem_mutation_allowed": False,
        "unrestricted_shell_allowed": False,
    },
    "decision": {
        "go_no_go": "GO_FOR_DESIGN_REVIEW_ONLY" if all_summaries_clean and all_failure_harnesses_pass else "NO_GO",
        "next_allowed_lane": "live_backup_creation_design_review_only",
        "next_forbidden_lane": "live_backup_creation_implementation",
        "reason": "Existing non-mutating proof lanes are clean; next step may design live backup creation but must not implement it yet." if all_summaries_clean and all_failure_harnesses_pass else "One or more proof lanes failed; do not proceed."
    },
    "notes": [
        "This checkpoint is non-mutating.",
        "This checkpoint does not create backups.",
        "This checkpoint does not bind backups.",
        "This checkpoint does not read or hash live source files.",
        "This checkpoint does not authorize executor dispatch.",
        "A later reviewed slice is required before any live backup creation implementation."
    ]
}

out.write_text(json.dumps(artifact, indent=2) + "\n")
print(out)
PY

  cmd_verify "$out" >/dev/null
  echo "$out"
}

cmd_verify() {
  need_cmd python3
  local file
  file="$(resolve_checkpoint_file "${1:-}")"

  assert_eq "$(json_get "$file" schema)" "spot.readiness_gate_checkpoint.v1" "schema"
  assert_eq "$(json_get "$file" phase)" "2.29" "phase"
  assert_eq "$(json_get "$file" mode)" "checkpoint_only_non_mutating" "mode"
  assert_eq "$(json_get "$file" checkpoint_status)" "ready_for_review_not_ready_for_live_execution" "checkpoint_status"

  assert_true "$(json_get "$file" readiness_gate.all_summaries_clean)" "all_summaries_clean"
  assert_true "$(json_get "$file" readiness_gate.all_failure_harnesses_pass)" "all_failure_harnesses_pass"
  assert_true "$(json_get "$file" readiness_gate.control_plane_ready_for_live_backup_design_review)" "control_plane_ready_for_live_backup_design_review"

  assert_false "$(json_get "$file" readiness_gate.live_backup_creation_allowed)" "live_backup_creation_allowed"
  assert_false "$(json_get "$file" readiness_gate.live_backup_binding_allowed)" "live_backup_binding_allowed"
  assert_false "$(json_get "$file" readiness_gate.live_source_file_reads_allowed)" "live_source_file_reads_allowed"
  assert_false "$(json_get "$file" readiness_gate.live_source_file_hashing_allowed)" "live_source_file_hashing_allowed"
  assert_false "$(json_get "$file" readiness_gate.checksum_generation_allowed)" "checksum_generation_allowed"
  assert_false "$(json_get "$file" readiness_gate.executor_dispatch_allowed)" "executor_dispatch_allowed"
  assert_false "$(json_get "$file" readiness_gate.execution_allowed)" "execution_allowed"
  assert_false "$(json_get "$file" readiness_gate.mutation_allowed)" "mutation_allowed"
  assert_false "$(json_get "$file" readiness_gate.mutation_performed)" "mutation_performed"
  assert_false "$(json_get "$file" readiness_gate.service_restart_allowed)" "service_restart_allowed"
  assert_false "$(json_get "$file" readiness_gate.config_write_allowed)" "config_write_allowed"
  assert_false "$(json_get "$file" readiness_gate.network_mutation_allowed)" "network_mutation_allowed"
  assert_false "$(json_get "$file" readiness_gate.direct_apply_allowed)" "direct_apply_allowed"
  assert_false "$(json_get "$file" readiness_gate.direct_admin_write_allowed)" "direct_admin_write_allowed"
  assert_false "$(json_get "$file" readiness_gate.direct_filesystem_mutation_allowed)" "direct_filesystem_mutation_allowed"
  assert_false "$(json_get "$file" readiness_gate.unrestricted_shell_allowed)" "unrestricted_shell_allowed"

  assert_eq "$(json_get "$file" decision.go_no_go)" "GO_FOR_DESIGN_REVIEW_ONLY" "go_no_go"
  assert_eq "$(json_get "$file" decision.next_allowed_lane)" "live_backup_creation_design_review_only" "next_allowed_lane"
  assert_eq "$(json_get "$file" decision.next_forbidden_lane)" "live_backup_creation_implementation" "next_forbidden_lane"

  echo "OK: readiness gate checkpoint verified: $file"
}

cmd_show() {
  local file
  file="$(resolve_checkpoint_file "${1:-}")"
  cat "$file"
}

cmd_list() {
  local count="${1:-20}"
  mkdir -p "$CHECKPOINT_DIR"
  find "$CHECKPOINT_DIR" -maxdepth 1 -type f -name 'READINESS-GATE-CHECKPOINT-*.json' -printf '%T@ %p\n' \
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
