#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
import time
import uuid
from pathlib import Path

ROOT = Path(os.environ.get("SPOT_RECEIPT_ROOT", "/mnt/collective/logs/spot/receipts"))
INDEX = ROOT / "index.jsonl"
ARTIFACTS = ROOT / "artifacts"

ALLOWED_PHASES = {"planned", "preflight", "noop", "blocked", "executed", "verified", "rollback", "halted"}

def utc():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

def load_json(path: str):
    p = Path(path)
    b = p.read_bytes()
    return p, b, json.loads(b.decode("utf-8"))

def existing_apply_ids():
    ids = set()
    if not INDEX.exists():
        return ids
    with INDEX.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                try:
                    rec = json.loads(line)
                    ids.add(rec.get("apply_attempt_id"))
                except Exception:
                    pass
    return ids

def append_jsonl(path: Path, rec: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, sort_keys=True, separators=(",", ":")) + "\n")

def main():
    ap = argparse.ArgumentParser(description="Write immutable Spot execution receipt")
    ap.add_argument("--correlation-id", required=True)
    ap.add_argument("--phase", required=True, choices=sorted(ALLOWED_PHASES))
    ap.add_argument("--input", required=True, help="JSON receipt input/proof file")
    ap.add_argument("--apply-attempt-id", default="")
    ap.add_argument("--lease-id", default="")
    ap.add_argument("--rollback-id", default="")
    ap.add_argument("--allow-executed", action="store_true", help="metadata only; does not grant execution")
    args = ap.parse_args()

    apply_id = args.apply_attempt_id.strip() or f"apply-{uuid.uuid4().hex}"

    if apply_id in existing_apply_ids():
        raise SystemExit(f"replay blocked: apply_attempt_id already exists: {apply_id}")

    p, b, payload = load_json(args.input)
    payload_sha = sha256_bytes(b)
    receipt_id = f"receipt-{uuid.uuid4().hex}"
    ts = utc()

    out_dir = ARTIFACTS / args.correlation_id
    out_dir.mkdir(parents=True, exist_ok=True)

    stored = out_dir / f"{ts.replace(':','')}-{args.phase}-{apply_id}-{payload_sha[:16]}.json"
    if stored.exists():
        raise SystemExit(f"refusing overwrite: {stored}")
    stored.write_bytes(b)

    rec = {
        "schema": "spot.execution_receipt.v1",
        "receipt_id": receipt_id,
        "ts": ts,
        "correlation_id": args.correlation_id,
        "apply_attempt_id": apply_id,
        "lease_id": args.lease_id,
        "rollback_id": args.rollback_id,
        "phase": args.phase,
        "input_original_path": str(p),
        "input_stored_path": str(stored),
        "input_sha256": payload_sha,
        "payload_summary": payload.get("summary", ""),
        "authority": "receipt_only",
        "spot_core_executor_only": True,
        "worker_self_apply": False,
        "replay_safe": True,
        "execution_allowed": False,
        "mutation_authority": False,
    }

    append_jsonl(INDEX, rec)

    print(json.dumps({
        "ok": True,
        "receipt_id": receipt_id,
        "correlation_id": args.correlation_id,
        "apply_attempt_id": apply_id,
        "phase": args.phase,
        "index": str(INDEX),
        "stored_path": str(stored),
        "execution_allowed": False,
        "mutation_authority": False,
        "replay_safe": True,
    }, indent=2, sort_keys=True))

if __name__ == "__main__":
    main()
