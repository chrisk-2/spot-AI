#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HISTORY_PATH = ROOT / "watch" / "state" / "execution-state-drift-history.jsonl"


def main() -> int:
    limit = 10
    if len(sys.argv) > 1:
        try:
            limit = max(1, int(sys.argv[1]))
        except ValueError:
            print("[FAIL] limit must be an integer")
            return 1

    if not HISTORY_PATH.exists():
        print("[]")
        return 0

    lines = [line.strip() for line in HISTORY_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]
    records = []
    for line in lines[-limit:]:
        records.append(json.loads(line))

    print(json.dumps(records, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
