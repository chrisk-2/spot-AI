#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HISTORY = ROOT / "watch" / "state" / "governance-closeout-history.jsonl"

if not HISTORY.exists():
    print("[]")
    raise SystemExit(0)

rows = [json.loads(x) for x in HISTORY.read_text().splitlines() if x.strip()]
print(json.dumps(rows[-10:], indent=2, sort_keys=True))
