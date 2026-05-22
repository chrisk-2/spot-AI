#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
import sys
import time
import uuid
from pathlib import Path

ROOT = Path(os.environ.get("SPOT_CHAIN_ROOT", "/mnt/collective/logs/spot/chains"))
INDEX = ROOT / "index.jsonl"
ARTIFACTS = ROOT / "artifacts"

ALLOWED_TYPES = {
    "review",
    "backup",
    "rollback",
    "apply",
    "governance",
    "validation",
    "note",
}

def now_utc():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def read_json_file(path: str):
    p = Path(path)
    data = p.read_bytes()
    try:
        parsed = json.loads(data.decode("utf-8"))
    except Exception as e:
        raise SystemExit(f"invalid json artifact: {path}: {e}")
    return p, data, parsed

def append_line(path: Path, obj: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(obj, sort_keys=True, separators=(",", ":")) + "\n"
    with path.open("a", encoding="utf-8") as f:
        f.write(line)

def main():
    ap = argparse.ArgumentParser(description="Write immutable Spot correlation chain entries")
    ap.add_argument("--correlation-id", default="")
    ap.add_argument("--artifact-type", required=True, choices=sorted(ALLOWED_TYPES))
    ap.add_argument("--artifact", required=True, help="JSON artifact path to bind")
    ap.add_argument("--source-id", default="")
    ap.add_argument("--note", default="")
    args = ap.parse_args()

    correlation_id = args.correlation_id.strip() or f"corr-{uuid.uuid4().hex}"
    artifact_path, artifact_bytes, parsed = read_json_file(args.artifact)
    artifact_sha = sha256_bytes(artifact_bytes)

    ts = now_utc()
    entry_id = f"chain-{uuid.uuid4().hex}"

    out_dir = ARTIFACTS / correlation_id
    out_dir.mkdir(parents=True, exist_ok=True)

    stored_name = f"{ts.replace(':','')}-{args.artifact_type}-{artifact_sha[:16]}.json"
    stored_path = out_dir / stored_name

    if stored_path.exists():
        raise SystemExit(f"refusing overwrite: {stored_path}")

    stored_path.write_bytes(artifact_bytes)

    record = {
        "schema": "spot.correlation_chain.v1",
        "entry_id": entry_id,
        "ts": ts,
        "correlation_id": correlation_id,
        "artifact_type": args.artifact_type,
        "source_id": args.source_id or parsed.get("review_id") or parsed.get("backup_id") or parsed.get("rollback_id") or parsed.get("apply_id") or parsed.get("governance_id") or parsed.get("validation_id") or "",
        "artifact_original_path": str(artifact_path),
        "artifact_stored_path": str(stored_path),
        "artifact_sha256": artifact_sha,
        "note": args.note,
        "authority": "correlation_only",
        "execution_allowed": False,
        "mutation_authority": False,
    }

    append_line(INDEX, record)

    print(json.dumps({
        "ok": True,
        "correlation_id": correlation_id,
        "entry_id": entry_id,
        "artifact_type": args.artifact_type,
        "artifact_sha256": artifact_sha,
        "index": str(INDEX),
        "stored_path": str(stored_path),
        "execution_allowed": False,
        "mutation_authority": False,
    }, indent=2, sort_keys=True))

if __name__ == "__main__":
    main()
