#!/usr/bin/env python3
import argparse
import json
import os
from pathlib import Path

JOURNAL = Path(os.environ.get("SPOT_NOOP_EXEC_ROOT", "/mnt/collective/logs/spot/noop-executor")) / "index.jsonl"

def main():
    ap = argparse.ArgumentParser(description="Show Spot noop executor records")
    ap.add_argument("correlation_id", nargs="?")
    ap.add_argument("--limit", type=int, default=25)
    args = ap.parse_args()

    if not JOURNAL.exists():
        raise SystemExit(f"missing journal: {JOURNAL}")

    rows = [json.loads(x) for x in JOURNAL.read_text().splitlines() if x.strip()]
    if args.correlation_id:
        rows = [r for r in rows if r.get("correlation_id") == args.correlation_id]
    rows = rows[-args.limit:]

    print(json.dumps({
        "ok": True,
        "count": len(rows),
        "items": rows,
        "execution_allowed": False,
        "mutation_authority": False
    }, indent=2, sort_keys=True))

if __name__ == "__main__":
    main()
