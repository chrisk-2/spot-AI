#!/usr/bin/env python3
import argparse, hashlib, json, os, time, uuid
from pathlib import Path

ROOT = Path(os.environ.get("SPOT_LEASE_ROOT", "/mnt/collective/logs/spot/leases"))
INDEX = ROOT / "index.jsonl"
ARTIFACTS = ROOT / "artifacts"

def utc():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

def sha(b):
    return hashlib.sha256(b).hexdigest()

def append(rec):
    INDEX.parent.mkdir(parents=True, exist_ok=True)
    with INDEX.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, sort_keys=True, separators=(",", ":")) + "\n")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--correlation-id", required=True)
    ap.add_argument("--owner", default="spot-core")
    ap.add_argument("--target", required=True)
    ap.add_argument("--action", required=True)
    ap.add_argument("--ttl-sec", type=int, default=900)
    args = ap.parse_args()

    lease_id = f"lease-{uuid.uuid4().hex}"
    ts = utc()
    payload = {
        "schema": "spot.execution_lease_payload.v1",
        "lease_id": lease_id,
        "correlation_id": args.correlation_id,
        "owner": args.owner,
        "target": args.target,
        "action": args.action,
        "ttl_sec": args.ttl_sec,
        "ts": ts,
        "spot_core_executor_only": True,
        "worker_self_apply": False,
        "execution_allowed": False,
        "mutation_authority": False
    }
    data = json.dumps(payload, sort_keys=True, indent=2).encode()
    digest = sha(data)

    out = ARTIFACTS / args.correlation_id
    out.mkdir(parents=True, exist_ok=True)
    stored = out / f"{ts.replace(':','')}-{lease_id}-{digest[:16]}.json"
    if stored.exists():
        raise SystemExit(f"refusing overwrite: {stored}")
    stored.write_bytes(data)

    rec = dict(payload)
    rec.update({
        "schema": "spot.execution_lease.v1",
        "payload_sha256": digest,
        "payload_stored_path": str(stored),
        "authority": "lease_only"
    })
    append(rec)
    print(json.dumps({"ok": True, "lease_id": lease_id, "correlation_id": args.correlation_id, "stored_path": str(stored), "execution_allowed": False, "mutation_authority": False}, indent=2, sort_keys=True))

if __name__ == "__main__":
    main()
