#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HISTORY = ROOT / "watch" / "state" / "deterministic-noop-execution-replay-history.jsonl"

limit = int(sys.argv[1]) if len(sys.argv) > 1 else 10

if not HISTORY.exists():
    print("[]")
    raise SystemExit(0)

rows = [json.loads(x) for x in HISTORY.read_text().splitlines() if x.strip()]
print(json.dumps(rows[-limit:], indent=2, sort_keys=True))
