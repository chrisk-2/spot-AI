#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
OPERATOR="$ROOT/watch/operator/spot-operator.sh"
# shellcheck source=/dev/null
source "$ROOT/watch/memory/memory-common.sh"

require_memory_root

CATEGORY_ROOT="$MEMORY_ROOT/strategy"
INDEX="$CATEGORY_ROOT/index.jsonl"
RECORD_ID="$(memory_id strategy)"
SNAPSHOT="$CATEGORY_ROOT/${RECORD_ID}.txt"

mkdir -p "$CATEGORY_ROOT"

set -o noclobber

{
  echo "===== SPOT STRATEGY MEMORY ====="
  echo "schema=spot.strategy-memory.v1"
  echo "record_id=$RECORD_ID"
  echo "timestamp=$(date -u -Is)"
  echo "observer=$(hostname)"
  echo "memory_class=validated-operational-strategy"
  echo "proposal_authority=false"
  echo "execution_authority=false"
  echo

  echo "===== LOCKED STRATEGY INVARIANTS ====="
  echo "spot_core_sole_executor=true"
  echo "worker_self_apply=false"
  echo "no_backup_no_change=true"
  echo "no_review_no_apply=true"
  echo "no_rollback_no_execution=true"
  echo "high_risk_network_changes_require_approval=true"
  echo

  echo "===== CURRENT GOVERNANCE POSTURE ====="
  timeout 240 "$OPERATOR" governance-sense 2>&1 || true
  echo

  echo "===== CURRENT FLEET HEALTH SUMMARY ====="
  timeout 600 "$OPERATOR" fleet-health 2>&1 |
    sed -n '1,250p' || true
  echo

  echo "===== VALIDATED REPOSITORY HISTORY ====="
  git -C "$ROOT" log \
    --date=iso-strict \
    --pretty=format:'%h %ad %s' \
    -25
  echo
  echo

  echo "===== JOURNAL COUNTS ====="

  for path in \
    /mnt/collective/logs/spot/reviews \
    /mnt/collective/logs/spot/actions \
    /mnt/collective/logs/spot/backups \
    /mnt/collective/logs/spot/rollbacks \
    /mnt/collective/logs/spot/learning
  do
    if [[ -d "$path" ]]; then
      count="$(find "$path" -type f 2>/dev/null | wc -l)"
      echo "journal_path=$path files=$count"
    else
      echo "journal_path=$path state=NOT-PRESENT"
    fi
  done

  echo
  echo "final_outcome=strategy_context_snapshot_created"
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
    "category": "strategy",
    "artifact": os.environ["SNAPSHOT"],
    "checksum": os.environ["CHECKSUM"],
    "authority": "historical-context-only",
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
