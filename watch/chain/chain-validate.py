#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

ROOT = Path(os.environ.get("SPOT_CHAIN_ROOT", "/mnt/collective/logs/spot/chains"))
INDEX = ROOT / "index.jsonl"

REQUIRED = {
    "schema",
    "entry_id",
    "ts",
    "correlation_id",
    "artifact_type",
    "artifact_stored_path",
    "artifact_sha256",
    "authority",
    "execution_allowed",
    "mutation_authority",
}

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def fail(msg):
    print(f"[FAIL] {msg}")
    raise SystemExit(1)

def main():
    ap = argparse.ArgumentParser(description="Validate Spot immutable correlation chain")
    ap.add_argument("--correlation-id", default="")
    ap.add_argument("--require-types", default="", help="comma-separated artifact types required for this correlation id")
    args = ap.parse_args()

    if not INDEX.exists():
        fail(f"missing index: {INDEX}")

    count = 0
    seen_entries = set()
    seen_by_corr = {}
    bad = 0

    with INDEX.open("r", encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            count += 1
            try:
                rec = json.loads(line)
            except Exception as e:
                fail(f"invalid JSONL line {lineno}: {e}")

            missing = REQUIRED - set(rec)
            if missing:
                fail(f"line {lineno} missing fields: {sorted(missing)}")

            if rec["schema"] != "spot.correlation_chain.v1":
                fail(f"line {lineno} bad schema: {rec['schema']}")

            if rec["entry_id"] in seen_entries:
                fail(f"duplicate entry_id: {rec['entry_id']}")
            seen_entries.add(rec["entry_id"])

            if rec.get("execution_allowed") is not False:
                fail(f"line {lineno} expands execution authority")

            if rec.get("mutation_authority") is not False:
                fail(f"line {lineno} expands mutation authority")

            if rec.get("authority") != "correlation_only":
                fail(f"line {lineno} bad authority: {rec.get('authority')}")

            stored = Path(rec["artifact_stored_path"])
            if not stored.exists():
                fail(f"line {lineno} missing stored artifact: {stored}")

            actual = sha256_file(stored)
            if actual != rec["artifact_sha256"]:
                fail(f"line {lineno} sha mismatch: {stored}")

            seen_by_corr.setdefault(rec["correlation_id"], set()).add(rec["artifact_type"])

    if args.correlation_id:
        if args.correlation_id not in seen_by_corr:
            fail(f"correlation_id not found: {args.correlation_id}")

        required = {x.strip() for x in args.require_types.split(",") if x.strip()}
        if required:
            present = seen_by_corr.get(args.correlation_id, set())
            missing = required - present
            if missing:
                fail(f"correlation_id {args.correlation_id} missing required types: {sorted(missing)}")

    print(json.dumps({
        "ok": True,
        "index": str(INDEX),
        "entries": count,
        "correlations": len(seen_by_corr),
        "validated": True,
        "execution_allowed": False,
        "mutation_authority": False,
    }, indent=2, sort_keys=True))

if __name__ == "__main__":
    main()
