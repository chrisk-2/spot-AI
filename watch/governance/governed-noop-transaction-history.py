#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HISTORY = ROOT / "watch" / "state" / "governed-noop-transaction-history.jsonl"


def main() -> int:
    limit = 10
    if len(sys.argv) > 1:
        try:
            limit = max(1, int(sys.argv[1]))
        except ValueError:
            print("[FAIL] limit must be integer")
            return 1

    if not HISTORY.exists():
        print("[]")
        return 0

    lines = [x.strip() for x in HISTORY.read_text(encoding="utf-8").splitlines() if x.strip()]
    rows = [json.loads(x) for x in lines[-limit:]]
    print(json.dumps(rows, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
