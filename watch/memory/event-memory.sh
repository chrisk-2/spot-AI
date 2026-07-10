#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# shellcheck source=/dev/null
source "$ROOT/watch/memory/memory-common.sh"

require_memory_root

CATEGORY_ROOT="$MEMORY_ROOT/events"
INDEX="$CATEGORY_ROOT/index.jsonl"
RECORD_ID="$(memory_id event)"
RECORD="$CATEGORY_ROOT/${RECORD_ID}.json"

mkdir -p "$CATEGORY_ROOT"

STATE_FILES=(
  "$ROOT/watch/state/fleet-status.json"
  "$ROOT/watch/state/routing-audit-summary.json"
  "$ROOT/watch/state/starfleet-online-check.json"
  "$ROOT/watch/state/self-heal-state.json"
  "$ROOT/watch/state/remediation-state.json"
)

STATE_JSON="$(
  python3 - "${STATE_FILES[@]}" <<'PY'
import hashlib
import json
import os
import sys

records = []

for name in sys.argv[1:]:
    if not os.path.isfile(name):
        records.append({
            "path": name,
            "present": False,
        })
        continue

    with open(name, "rb") as handle:
        payload = handle.read()

    records.append({
        "path": name,
        "present": True,
        "size_bytes": len(payload),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "modified_epoch": int(os.path.getmtime(name)),
    })

print(json.dumps(records, separators=(",", ":")))
PY
)"

RECORD_JSON="$(
  RECORD_ID="$RECORD_ID" \
  STATE_JSON="$STATE_JSON" \
  python3 - <<'PY'
import json
import os
from datetime import datetime, timezone

record = {
    "schema": "spot.event-memory.v1",
    "record_id": os.environ["RECORD_ID"],
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "observer": os.uname().nodename,
    "category": "event",
    "authority": "observation_only",
    "mutation_authority": False,
    "source_state": json.loads(os.environ["STATE_JSON"]),
}

print(json.dumps(record, indent=2, sort_keys=True))
PY
)"

set -o noclobber
printf '%s\n' "$RECORD_JSON" >"$RECORD"
set +o noclobber

CHECKSUM="$(write_checksum "$RECORD")"

INDEX_RECORD="$(
  RECORD="$RECORD" \
  RECORD_ID="$RECORD_ID" \
  CHECKSUM="$CHECKSUM" \
  python3 - <<'PY'
import json
import os
from datetime import datetime, timezone

print(json.dumps({
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "record_id": os.environ["RECORD_ID"],
    "category": "event",
    "artifact": os.environ["RECORD"],
    "checksum": os.environ["CHECKSUM"],
    "append_only": True,
}, separators=(",", ":")))
PY
)"

append_json_line "$INDEX" "$INDEX_RECORD"

echo "record: $RECORD"
echo "checksum: $CHECKSUM"
echo "index: $INDEX"
echo "existing_records_modified: false"
echo "mutation_scope: append-only-memory"
