#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 3 ]]; then
  echo "usage: $0 <worker> <remote_path> <local_content_file>" >&2
  exit 1
fi

WORKER="$1"
REMOTE_PATH="$2"
LOCAL_CONTENT_FILE="$3"

if [[ ! -f "$LOCAL_CONTENT_FILE" ]]; then
  echo "local content file not found: $LOCAL_CONTENT_FILE" >&2
  exit 1
fi

python3 - <<'PY' "$WORKER" "$REMOTE_PATH" "$LOCAL_CONTENT_FILE"
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, "/home/ogre/spot-stack/watch")
from spot_mcp_client import SpotClient

worker = sys.argv[1]
remote_path = sys.argv[2]
local_content_file = Path(sys.argv[3])

content = local_content_file.read_text(encoding="utf-8")

client = SpotClient()
result = client.write_file(worker=worker, path=remote_path, content=content)
print(json.dumps(result, indent=2, sort_keys=True))
PY
