#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
import time
import uuid
from pathlib import Path

ROOT = Path(os.environ.get("SPOT_APPROVAL_ROOT", "/mnt/collective/logs/spot/approvals"))
INDEX = ROOT / "index.jsonl"
ARTIFACTS = ROOT / "artifacts"

ALLOWED_RISK = {"low", "medium", "high"}
ALLOWED_DECISION = {"required", "approved", "denied", "blocked"}

def utc():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

def sha_bytes(data):
    return hashlib.sha256(data).hexdigest()

def append_jsonl(path, rec):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, sort_keys=True, separators=(",", ":")) + "\n")

def main():
    ap = argparse.ArgumentParser(description="Write Spot approval escalation record")
    ap.add_argument("--correlation-id", required=True)
    ap.add_argument("--risk-class", required=True, choices=sorted(ALLOWED_RISK))
    ap.add_argument("--decision", required=True, choices=sorted(ALLOWED_DECISION))
    ap.add_argument("--reason", required=True)
    ap.add_argument("--operator", default="ogre")
    args = ap.parse_args()

    approval_id = f"approval-{uuid.uuid4().hex}"
    ts = utc()

    payload = {
        "schema": "spot.approval_escalation_payload.v1",
        "approval_id": approval_id,
        "correlation_id": args.correlation_id,
        "risk_class": args.risk_class,
        "decision": args.decision,
        "reason": args.reason,
        "operator": args.operator,
        "ts": ts,
        "authority": "approval_record_only",
        "spot_core_executor_only": True,
        "worker_self_apply": False,
        "execution_allowed": False,
        "mutation_authority": False
    }

    data = json.dumps(payload, indent=2, sort_keys=True).encode()
    digest = sha_bytes(data)

    out = ARTIFACTS / args.correlation_id
    out.mkdir(parents=True, exist_ok=True)
    stored = out / f"{ts.replace(':','')}-{approval_id}-{digest[:16]}.json"

    stored.write_bytes(data)

    rec = dict(payload)
    rec["schema"] = "spot.approval_escalation.v1"
    rec["payload_sha256"] = digest
    rec["payload_stored_path"] = str(stored)

    append_jsonl(INDEX, rec)

    print(json.dumps({
        "ok": True,
        "approval_id": approval_id,
        "correlation_id": args.correlation_id,
        "risk_class": args.risk_class,
        "decision": args.decision,
        "stored_path": str(stored),
        "execution_allowed": False,
        "mutation_authority": False
    }, indent=2, sort_keys=True))

if __name__ == "__main__":
    main()
