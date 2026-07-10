#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
OPERATOR="$ROOT/watch/operator/spot-operator.sh"
# shellcheck source=/dev/null
source "$ROOT/watch/memory/memory-common.sh"

require_memory_root

CATEGORY_ROOT="$MEMORY_ROOT/infrastructure"
INDEX="$CATEGORY_ROOT/index.jsonl"
RECORD_ID="$(memory_id infrastructure)"
SNAPSHOT="$CATEGORY_ROOT/${RECORD_ID}.txt"

mkdir -p "$CATEGORY_ROOT"

set -o noclobber

{
  echo "===== SPOT INFRASTRUCTURE MEMORY ====="
  echo "schema=spot.infrastructure-memory.v1"
  echo "record_id=$RECORD_ID"
  echo "timestamp=$(date -u -Is)"
  echo "observer=$(hostname)"
  echo "authority=observation_only"
  echo "mutation_authority=false"
  echo

  echo "===== TOPOLOGY ====="
  timeout 180 "$OPERATOR" topology-sense 2>&1 || true
  echo

  echo "===== RESOURCES ====="
  timeout 180 "$OPERATOR" resource-sense 2>&1 || true
  echo

  echo "===== STORAGE ====="
  timeout 180 "$OPERATOR" mount-sense 2>&1 || true
  echo

  echo "===== WORKER RUNTIME ====="
  timeout 180 "$OPERATOR" worker-runtime-sense 2>&1 || true
  echo

  echo "===== CERTIFICATES ====="
  timeout 300 "$OPERATOR" certificate-sense 2>&1 || true
  echo

  echo "final_outcome=infrastructure_snapshot_created"
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
    "category": "infrastructure",
    "artifact": os.environ["SNAPSHOT"],
    "checksum": os.environ["CHECKSUM"],
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
