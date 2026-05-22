#!/usr/bin/env python3
import argparse
import json
import os
from pathlib import Path

ROOT = Path(os.environ.get("SPOT_RECEIPT_ROOT", "/mnt/collective/logs/spot/receipts"))
INDEX = ROOT / "index.jsonl"

def main():
    ap = argparse.ArgumentParser(description="Show Spot execution receipts")
    ap.add_argument("correlation_id", nargs="?")
    ap.add_argument("--limit", type=int, default=25)
    args = ap.parse_args()

    if not INDEX.exists():
        raise SystemExit(f"missing index: {INDEX}")

    rows = []
    with INDEX.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            rec = json.loads(line)
            if args.correlation_id and rec.get("correlation_id") != args.correlation_id:
                continue
            rows.append(rec)

    rows = rows[-args.limit:]

    print(json.dumps({
        "ok": True,
        "index": str(INDEX),
        "count": len(rows),
        "items": rows,
        "execution_allowed": False,
        "mutation_authority": False,
    }, indent=2, sort_keys=True))

if __name__ == "__main__":
    main()
