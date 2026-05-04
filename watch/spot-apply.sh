#!/usr/bin/env bash
set -Eeuo pipefail

BASE_DIR="${BASE_DIR:-/home/ogre/spot-stack/watch}"
BACKUP_ROOT="${BACKUP_ROOT:-/mnt/collective/backups/spot-core/supervised-apply}"
RUN_DIR="${RUN_DIR:-${BASE_DIR}/execution-runs}"
SPOT_CLIENT="${SPOT_CLIENT:-${BASE_DIR}/spot-client.sh}"

usage(){ cat <<'EOF'
Usage:
  spot-apply.sh execute-handoff <handoff-id-or-file>
  spot-apply.sh runs [count]
  spot-apply.sh show-run <run-id-or-file>
  spot-apply.sh verify-run <run-id-or-file>

execute-handoff is non-mutating. It verifies the reviewed handoff, runs live prechecks,
creates a verified backup artifact, writes an execution-run contract, then stops.
EOF
}

need_cmd(){ command -v "$1" >/dev/null 2>&1 || { echo "ERROR: required command not found: $1" >&2; exit 2; }; }
stamp(){ date -u +%Y%m%d-%H%M%S; }

line_value(){
  local file="$1" key="$2"
  awk -F': ' -v k="$key" '$1==k {print substr($0, index($0, ": ")+2); exit}' "$file"
}

resolve_handoff_file(){
  local id="${1:-}"
  [[ -n "$id" ]] || { echo "ERROR: execution handoff id/file required" >&2; exit 2; }
  local file="$id"
  [[ -f "$file" ]] || file="${BASE_DIR}/execution-handoffs/${id%.md}.md"
  [[ -f "$file" ]] || file="${BASE_DIR}/execution-handoffs/HANDOFF-${id#HANDOFF-}.md"
  [[ -f "$file" ]] || { echo "ERROR: execution handoff not found: $id" >&2; exit 2; }
  printf '%s' "$file"
}

resolve_run_file(){
  local id="${1:-}"
  [[ -n "$id" ]] || { echo "ERROR: run id/file required" >&2; exit 2; }
  local file="$id"
  [[ -f "$file" ]] || file="${RUN_DIR}/${id%.md}.md"
  [[ -f "$file" ]] || file="${RUN_DIR}/RUN-${id#RUN-}.md"
  [[ -f "$file" ]] || { echo "ERROR: run not found: $id" >&2; exit 2; }
  printf '%s' "$file"
}

extract_section(){
  local file="$1" section="$2"
  python3 - "$file" "$section" <<'PY'
from pathlib import Path
import re, sys
text = Path(sys.argv[1]).read_text(errors="ignore")
name = sys.argv[2]
m = re.search(rf'^{re.escape(name)}\s*\n(?P<body>.*?)(?=\n[A-Z_]+\s*\n|\Z)', text, re.M | re.S)
print(m.group('body').strip() if m else "")
PY
}

section_bullets(){
  local file="$1" section="$2"
  extract_section "$file" "$section" | sed -n 's/^- //p'
}

verify_handoff_static(){
  local handoff="$1"
  "$SPOT_CLIENT" execution-handoff-verify "$handoff" >/dev/null
  local risk
  risk="$(line_value "$handoff" risk_class)"
  case "$risk" in low|medium|high) ;; *) echo "ERROR: invalid risk_class in handoff: ${risk:-<missing>}" >&2; exit 2;; esac
  [[ "$(line_value "$handoff" execution_allowed)" == "false" ]] || { echo "ERROR: execution_allowed must be false for dry-run wrapper" >&2; exit 2; }
  [[ "$(line_value "$handoff" mutation_allowed)" == "false" ]] || { echo "ERROR: mutation_allowed must be false" >&2; exit 2; }
  [[ "$(line_value "$handoff" backup_required)" == "true" ]] || { echo "ERROR: backup_required must be true" >&2; exit 2; }
  [[ "$(line_value "$handoff" backup_bound)" == "false" ]] || { echo "ERROR: backup_bound must be false before wrapper run" >&2; exit 2; }
  [[ "$(line_value "$handoff" backup_artifact)" == "pending" ]] || { echo "ERROR: backup_artifact must be pending before wrapper run" >&2; exit 2; }
}

run_prechecks(){
  local handoff="$1" log="$2"
  local commands=()
  mapfile -t commands < <(section_bullets "$handoff" PRECHECK_VALIDATION | awk 'NF && !seen[$0]++')
  [[ ${#commands[@]} -gt 0 ]] || { echo "ERROR: no PRECHECK_VALIDATION commands found" >&2; exit 2; }
  {
    echo "PRECHECK_RESULTS"
    for cmd in "${commands[@]}"; do
      echo
      echo "COMMAND: $cmd"
      echo "START_UTC: $(stamp)"
      if bash -lc "$cmd"; then
        echo "RESULT: PASS"
      else
        local rc=$?
        echo "RESULT: FAIL rc=$rc"
        echo "END_UTC: $(stamp)"
        return "$rc"
      fi
      echo "END_UTC: $(stamp)"
    done
  } >> "$log" 2>&1
}

create_backup(){
  local handoff="$1" apply_plan="$2" proposal="$3" backup_dir="$4"
  mkdir -p "$backup_dir/files" "$backup_dir/artifacts"
  cp -a "$handoff" "$backup_dir/artifacts/"
  cp -a "$apply_plan" "$backup_dir/artifacts/"
  cp -a "$proposal" "$backup_dir/artifacts/"
  local target copied=0 safe
  while IFS= read -r target; do
    [[ -n "$target" ]] || continue
    [[ "$target" = /* ]] || continue
    [[ -f "$target" ]] || { echo "ERROR: target file missing during backup: $target" >&2; exit 2; }
    safe="$(printf '%s' "$target" | sed 's#^/##; s#[/]#__#g')"
    cp -a "$target" "$backup_dir/files/${safe}"
    copied=$((copied+1))
  done < <(section_bullets "$handoff" TARGET_FILES)
  [[ "$copied" -gt 0 ]] || { echo "ERROR: no target files copied into backup" >&2; exit 2; }
  (cd "$backup_dir" && find . -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 sha256sum > SHA256SUMS)
  (cd "$backup_dir" && sha256sum -c SHA256SUMS >/dev/null)
  python3 - "$handoff" "$apply_plan" "$proposal" "$backup_dir" "$copied" <<'PY'
from pathlib import Path
from datetime import datetime, UTC
import json, sys
handoff, apply_plan, proposal, backup_dir, copied = sys.argv[1:]
meta = {
  "created_utc": datetime.now(UTC).strftime("%Y%m%d-%H%M%S"),
  "policy": "no_backup_no_change",
  "mode": "supervised_apply_dry_run",
  "mutation_performed": False,
  "handoff": handoff,
  "apply_plan": apply_plan,
  "proposal": proposal,
  "target_file_count": int(copied),
}
Path(backup_dir, "metadata.json").write_text(json.dumps(meta, indent=2) + "\n")
PY
  (cd "$backup_dir" && find . -type f ! -name SHA256SUMS -print0 | sort -z | xargs -0 sha256sum > SHA256SUMS)
  (cd "$backup_dir" && sha256sum -c SHA256SUMS >/dev/null)
}

write_run_contract(){
  local run_file="$1" handoff="$2" apply_plan="$3" proposal="$4" backup_dir="$5" precheck_log="$6"
  local run_id handoff_id risk
  run_id="$(basename "$run_file" .md)"
  handoff_id="$(basename "$handoff" .md)"
  risk="$(line_value "$handoff" risk_class)"
  cat > "$run_file" <<EOF
# Spot Execution Run ${run_id}

linked_execution_handoff: ${handoff_id}
linked_apply_plan: $(basename "$apply_plan" .md)
linked_proposal: $(basename "$proposal" .md)
created_utc: $(stamp)
risk_class: ${risk}
run_status: prepared_backup_bound_dry_run
execution_allowed: false
mutation_allowed: false
mutation_performed: false
backup_required: true
backup_bound: true
backup_artifact: ${backup_dir}
backup_verified: true
policy_class: supervised_apply_execution_run
autonomy_level: 1
execution_wrapper: spot-apply.sh
approval_gate: mutation_plugin_not_enabled
rollback_required: true
rollback_authority: recorded_prechange_backup_only
precheck_log: ${precheck_log}

---

RESULT
- Reviewed execution handoff verified.
- Live prechecks completed successfully.
- Pre-change backup artifact created and checksum-verified.
- No mutation was performed.
- Execution intentionally stopped before mutation plugin dispatch.

BACKUP_CONTENTS
- Target files from TARGET_FILES.
- Source execution handoff.
- Linked apply plan.
- Linked proposal.
- metadata.json.
- SHA256SUMS.

NEXT_ALLOWED_ACTION
- Manual review of this execution-run contract.
- Future Phase 1.7 mutation plugin may consume this run only after an explicit additional approval gate.

POLICY_GATES
- No backup, no change.
- Backup artifact is bound before mutation.
- This run is non-mutating.
- Rollback authority is the recorded backup artifact only.
EOF
}

cmd_execute_handoff(){
  need_cmd python3
  need_cmd sha256sum
  need_cmd awk
  need_cmd sed
  local handoff apply_id proposal_id apply_plan proposal ts run_id run_file backup_dir precheck_log
  handoff="$(resolve_handoff_file "${1:-}")"
  verify_handoff_static "$handoff"
  apply_id="$(line_value "$handoff" linked_apply_plan)"
  proposal_id="$(line_value "$handoff" linked_proposal)"
  apply_plan="${BASE_DIR}/apply-plans/${apply_id}.md"
  proposal="${BASE_DIR}/proposals/${proposal_id}.md"
  [[ -f "$apply_plan" ]] || { echo "ERROR: linked apply plan missing: $apply_plan" >&2; exit 2; }
  [[ -f "$proposal" ]] || { echo "ERROR: linked proposal missing: $proposal" >&2; exit 2; }
  ts="$(stamp)"
  run_id="RUN-$(basename "$handoff" .md)-${ts}"
  mkdir -p "$RUN_DIR" "$BACKUP_ROOT"
  run_file="${RUN_DIR}/${run_id}.md"
  precheck_log="${RUN_DIR}/${run_id}.precheck.log"
  backup_dir="${BACKUP_ROOT}/${run_id}"
  run_prechecks "$handoff" "$precheck_log"
  create_backup "$handoff" "$apply_plan" "$proposal" "$backup_dir"
  write_run_contract "$run_file" "$handoff" "$apply_plan" "$proposal" "$backup_dir" "$precheck_log"
  cmd_verify_run "$run_file" >/dev/null
  echo "[execution-run-prepared] $run_file"
  echo "[backup-bound] $backup_dir"
  echo "[mutation] skipped: dry-run wrapper only"
}

cmd_runs(){
  local count="${1:-20}"
  mkdir -p "$RUN_DIR"
  find "$RUN_DIR" -maxdepth 1 -type f -name 'RUN-*.md' -printf '%T@ %f\n' 2>/dev/null | sort -nr | head -n "$count" | awk '{print $2}'
}

cmd_show_run(){
  local file
  file="$(resolve_run_file "${1:-}")"
  cat "$file"
}

cmd_verify_run(){
  local file backup precheck
  file="$(resolve_run_file "${1:-}")"
  [[ "$(line_value "$file" run_status)" == "prepared_backup_bound_dry_run" ]] || { echo "ERROR: run_status invalid" >&2; exit 2; }
  [[ "$(line_value "$file" execution_allowed)" == "false" ]] || { echo "ERROR: execution_allowed must be false" >&2; exit 2; }
  [[ "$(line_value "$file" mutation_allowed)" == "false" ]] || { echo "ERROR: mutation_allowed must be false" >&2; exit 2; }
  [[ "$(line_value "$file" mutation_performed)" == "false" ]] || { echo "ERROR: mutation_performed must be false" >&2; exit 2; }
  [[ "$(line_value "$file" backup_bound)" == "true" ]] || { echo "ERROR: backup_bound must be true" >&2; exit 2; }
  [[ "$(line_value "$file" backup_verified)" == "true" ]] || { echo "ERROR: backup_verified must be true" >&2; exit 2; }
  backup="$(line_value "$file" backup_artifact)"
  precheck="$(line_value "$file" precheck_log)"
  [[ -d "$backup" ]] || { echo "ERROR: backup artifact missing: $backup" >&2; exit 2; }
  [[ -f "$backup/SHA256SUMS" ]] || { echo "ERROR: backup SHA256SUMS missing" >&2; exit 2; }
  (cd "$backup" && sha256sum -c SHA256SUMS >/dev/null)
  [[ -f "$precheck" ]] || { echo "ERROR: precheck log missing: $precheck" >&2; exit 2; }
  if grep -q 'RESULT: FAIL' "$precheck"; then
    echo "ERROR: precheck log contains failure" >&2
    exit 2
  fi
  echo "RESULT: PASS run=$(basename "$file" .md)"
}

main(){
  local cmd="${1:-}"
  shift || true
  case "$cmd" in
    execute-handoff) cmd_execute_handoff "$@";;
    runs) cmd_runs "$@";;
    show-run) cmd_show_run "$@";;
    verify-run) cmd_verify_run "$@";;
    -h|--help|"") usage;;
    *) usage; exit 2;;
  esac
}

main "$@"
