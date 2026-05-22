#!/usr/bin/env python3
import argparse, hashlib, json, os, time, uuid
from pathlib import Path

ROOT = Path(os.environ.get("SPOT_ROLLBACK_ROOT", "/mnt/collective/logs/spot/rollbacks"))
INDEX = ROOT / "index.jsonl"
ARTIFACTS = ROOT / "artifacts"

def utc():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

def sha(b):
    return hashlib.sha256(b).hexdigest()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--correlation-id", required=True)
    ap.add_argument("--target", required=True)
    ap.add_argument("--plan", required=True)
    ap.add_argument("--backup-path", required=True)
    args = ap.parse_args()

    rollback_id = f"rollback-{uuid.uuid4().hex}"
    ts = utc()
    payload = {
        "schema": "spot.rollback_receipt_payload.v1",
        "rollback_id": rollback_id,
        "correlation_id": args.correlation_id,
        "target": args.target,
        "plan": args.plan,
        "backup_path": args.backup_path,
        "rollback_defined": True,
        "rollback_executed": False,
        "ts": ts,
        "execution_allowed": False,
        "mutation_authority": False
    }
    data = json.dumps(payload, sort_keys=True, indent=2).encode()
    digest = sha(data)
    out = ARTIFACTS / args.correlation_id
    out.mkdir(parents=True, exist_ok=True)
    stored = out / f"{ts.replace(':','')}-{rollback_id}-{digest[:16]}.json"
    if stored.exists():
        raise SystemExit(f"refusing overwrite: {stored}")
    stored.write_bytes(data)

    rec = dict(payload)
    rec.update({"schema": "spot.rollback_receipt.v1", "payload_sha256": digest, "payload_stored_path": str(stored), "authority": "rollback_receipt_only"})
    INDEX.parent.mkdir(parents=True, exist_ok=True)
    with INDEX.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, sort_keys=True, separators=(",", ":")) + "\n")

    print(json.dumps({"ok": True, "rollback_id": rollback_id, "correlation_id": args.correlation_id, "stored_path": str(stored), "execution_allowed": False, "mutation_authority": False}, indent=2, sort_keys=True))
if __name__ == "__main__":
    main()
