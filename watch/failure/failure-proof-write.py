#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
import time
import uuid
from pathlib import Path

ROOT = Path(os.environ.get("SPOT_FAILURE_ROOT", "/mnt/collective/logs/spot/failure-proofs"))
INDEX = ROOT / "index.jsonl"
ARTIFACTS = ROOT / "artifacts"

ALLOWED_FAILURE = {
    "preflight_block",
    "missing_backup",
    "missing_rollback",
    "duplicate_replay",
    "executor_crash",
    "validation_fail",
    "operator_denied"
}

def utc():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

def sha_bytes(data):
    return hashlib.sha256(data).hexdigest()

def append_jsonl(path, rec):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, sort_keys=True, separators=(",", ":")) + "\n")

def main():
    ap = argparse.ArgumentParser(description="Write Spot failure/crash proof")
    ap.add_argument("--correlation-id", required=True)
    ap.add_argument("--failure-type", required=True, choices=sorted(ALLOWED_FAILURE))
    ap.add_argument("--expected-result", default="blocked")
    ap.add_argument("--evidence", required=True)
    args = ap.parse_args()

    proof_id = f"failure-{uuid.uuid4().hex}"
    ts = utc()

    payload = {
        "schema": "spot.failure_proof_payload.v1",
        "proof_id": proof_id,
        "correlation_id": args.correlation_id,
        "failure_type": args.failure_type,
        "expected_result": args.expected_result,
        "evidence": args.evidence,
        "ts": ts,
        "safe_failure": True,
        "rollback_required": False,
        "rollback_executed": False,
        "execution_allowed": False,
        "mutation_authority": False,
        "authority": "failure_proof_only"
    }

    data = json.dumps(payload, indent=2, sort_keys=True).encode()
    digest = sha_bytes(data)

    out = ARTIFACTS / args.correlation_id
    out.mkdir(parents=True, exist_ok=True)
    stored = out / f"{ts.replace(':','')}-{proof_id}-{digest[:16]}.json"

    stored.write_bytes(data)

    rec = dict(payload)
    rec["schema"] = "spot.failure_proof.v1"
    rec["payload_sha256"] = digest
    rec["payload_stored_path"] = str(stored)

    append_jsonl(INDEX, rec)

    print(json.dumps({
        "ok": True,
        "proof_id": proof_id,
        "correlation_id": args.correlation_id,
        "failure_type": args.failure_type,
        "safe_failure": True,
        "stored_path": str(stored),
        "execution_allowed": False,
        "mutation_authority": False
    }, indent=2, sort_keys=True))

if __name__ == "__main__":
    main()
