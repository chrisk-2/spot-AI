#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
OPERATOR="$ROOT/watch/operator/spot-operator.sh"
# shellcheck source=/dev/null
source "$ROOT/watch/memory/memory-common.sh"

require_memory_root

CATEGORY_ROOT="$MEMORY_ROOT/operator"
INDEX="$CATEGORY_ROOT/index.jsonl"
RECORD_ID="$(memory_id operator)"
SNAPSHOT="$CATEGORY_ROOT/${RECORD_ID}.txt"

mkdir -p "$CATEGORY_ROOT"

REFERENCE_FILES=(
  "STATE.md"
  "spot_roadmap_stages.md"
  "watch/operator/spot-operator.sh"
  "watch/review/WORKER-05-QC-STANDARD.md"
)

set -o noclobber

{
  echo "===== SPOT OPERATOR MEMORY ====="
  echo "schema=spot.operator-memory.v1"
  echo "record_id=$RECORD_ID"
  echo "timestamp=$(date -u -Is)"
  echo "observer=$(hostname)"
  echo "memory_class=declared-workflow-and-policy"
  echo "inferred_personal_attributes=false"
  echo "mutation_authority=false"
  echo

  echo "===== DECLARED MODULE WORKFLOW ====="
  echo "terminology=module"
  echo "batch_related_modules=true"
  echo "final_block_runs_validation_commit_push=true"
  echo "explicit_git_staging=true"
  echo "runtime_drift_file=starfleet-ui/public/status.json"
  echo "validation_failure_policy=fix_only_failing_layer"
  echo

  echo "===== OPERATOR COMMAND BOUNDARIES ====="
  timeout 120 "$OPERATOR" command-map 2>&1 || true
  echo

  echo "===== REFERENCE ARTIFACT HASHES ====="

  for relative in "${REFERENCE_FILES[@]}"; do
    path="$ROOT/$relative"

    if [[ -f "$path" ]]; then
      sha256sum "$path"
    else
      echo "NOT-PRESENT $relative"
    fi
  done

  echo
  echo "===== REPOSITORY POSITION ====="
  git -C "$ROOT" status --short --branch
  git -C "$ROOT" log --oneline -10
  echo

  echo "final_outcome=operator_context_snapshot_created"
} >"$SNAPSHOT"

set +o noclobber

CHECKSUM="$(write_checksum "$SNAPSHOT")"

INDEX_RECORD="$(
  RECORD_ID="$RECORD_ID" \
  SNAPSHOT="$SNAPSHOT" \
  CHECKSUM="$CHECKSUM" \
  python3 - <<'PY'
import json
import os
from datetime import datetime, timezone

print(json.dumps({
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "record_id": os.environ["RECORD_ID"],
    "category": "operator",
    "artifact": os.environ["SNAPSHOT"],
    "checksum": os.environ["CHECKSUM"],
    "source": "declared-workflow-and-repository-policy",
    "append_only": True,
}, separators=(",", ":")))
PY
)"

append_json_line "$INDEX" "$INDEX_RECORD"

echo "record: $SNAPSHOT"
echo "checksum: $CHECKSUM"
echo "index: $INDEX"
echo "existing_records_modified: false"
echo "mutation_scope: append-only-memory"
