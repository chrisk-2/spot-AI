#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
from pathlib import Path

ROOT = Path(os.environ.get("SPOT_RECEIPT_ROOT", "/mnt/collective/logs/spot/receipts"))
INDEX = ROOT / "index.jsonl"

REQUIRED = {
    "schema",
    "receipt_id",
    "ts",
    "correlation_id",
    "apply_attempt_id",
    "phase",
    "input_stored_path",
    "input_sha256",
    "authority",
    "spot_core_executor_only",
    "worker_self_apply",
    "replay_safe",
    "execution_allowed",
    "mutation_authority",
}

def fail(msg):
    print(f"[FAIL] {msg}")
    raise SystemExit(1)

def sha256_file(path: Path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()

def main():
    ap = argparse.ArgumentParser(description="Validate Spot execution receipts")
    ap.add_argument("--correlation-id", default="")
    args = ap.parse_args()

    if not INDEX.exists():
        fail(f"missing index: {INDEX}")

    count = 0
    receipts = set()
    apply_ids = set()
    correlations = set()

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

            if rec["schema"] != "spot.execution_receipt.v1":
                fail(f"line {lineno} bad schema")

            if rec["receipt_id"] in receipts:
                fail(f"duplicate receipt_id: {rec['receipt_id']}")
            receipts.add(rec["receipt_id"])

            if rec["apply_attempt_id"] in apply_ids:
                fail(f"replay detected duplicate apply_attempt_id: {rec['apply_attempt_id']}")
            apply_ids.add(rec["apply_attempt_id"])

            if rec["authority"] != "receipt_only":
                fail(f"line {lineno} bad authority")

            if rec["spot_core_executor_only"] is not True:
                fail(f"line {lineno} executor invariant failed")

            if rec["worker_self_apply"] is not False:
                fail(f"line {lineno} worker self-apply invariant failed")

            if rec["replay_safe"] is not True:
                fail(f"line {lineno} replay_safe invariant failed")

            if rec["execution_allowed"] is not False:
                fail(f"line {lineno} execution authority expansion")

            if rec["mutation_authority"] is not False:
                fail(f"line {lineno} mutation authority expansion")

            stored = Path(rec["input_stored_path"])
            if not stored.exists():
                fail(f"line {lineno} missing stored input: {stored}")

            if sha256_file(stored) != rec["input_sha256"]:
                fail(f"line {lineno} sha mismatch: {stored}")

            correlations.add(rec["correlation_id"])

    if args.correlation_id and args.correlation_id not in correlations:
        fail(f"correlation_id not found: {args.correlation_id}")

    print(json.dumps({
        "ok": True,
        "index": str(INDEX),
        "entries": count,
        "correlations": len(correlations),
        "validated": True,
        "execution_allowed": False,
        "mutation_authority": False,
        "replay_safe": True,
    }, indent=2, sort_keys=True))

if __name__ == "__main__":
    main()
