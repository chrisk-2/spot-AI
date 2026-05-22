#!/usr/bin/env python3
import argparse, json, os
from pathlib import Path

INDEX = Path(os.environ.get("SPOT_LEASE_ROOT", "/mnt/collective/logs/spot/leases")) / "index.jsonl"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("correlation_id", nargs="?")
    ap.add_argument("--limit", type=int, default=25)
    args = ap.parse_args()
    if not INDEX.exists():
        raise SystemExit(f"missing index: {INDEX}")
    rows = [json.loads(x) for x in INDEX.read_text().splitlines() if x.strip()]
    if args.correlation_id:
        rows = [r for r in rows if r.get("correlation_id") == args.correlation_id]
    print(json.dumps({"ok": True, "count": len(rows[-args.limit:]), "items": rows[-args.limit:], "execution_allowed": False, "mutation_authority": False}, indent=2, sort_keys=True))
if __name__ == "__main__":
    main()
