#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
import time
import uuid
from pathlib import Path

ROOT = Path(os.environ.get("SPOT_LEARNING_ROOT", "/mnt/collective/logs/spot/learning"))
INDEX = ROOT / "index.jsonl"
ARTIFACTS = ROOT / "artifacts"

def utc():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

def sha_bytes(data):
    return hashlib.sha256(data).hexdigest()

def append_jsonl(path, rec):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, sort_keys=True, separators=(",", ":")) + "\n")

def main():
    ap = argparse.ArgumentParser(description="Write proposal-only learning recommendation")
    ap.add_argument("--correlation-id", required=True)
    ap.add_argument("--lesson", required=True)
    ap.add_argument("--recommendation", required=True)
    args = ap.parse_args()

    learning_id = f"learning-{uuid.uuid4().hex}"
    ts = utc()

    payload = {
        "schema": "spot.learning_proposal_payload.v1",
        "learning_id": learning_id,
        "correlation_id": args.correlation_id,
        "lesson": args.lesson,
        "recommendation": args.recommendation,
        "ts": ts,
        "proposal_only": True,
        "requires_review": True,
        "auto_apply": False,
        "execution_allowed": False,
        "mutation_authority": False,
        "authority": "learning_proposal_only"
    }

    data = json.dumps(payload, indent=2, sort_keys=True).encode()
    digest = sha_bytes(data)

    out = ARTIFACTS / args.correlation_id
    out.mkdir(parents=True, exist_ok=True)

    stored = out / f"{ts.replace(':','')}-{learning_id}-{digest[:16]}.json"
    stored.write_bytes(data)

    rec = dict(payload)
    rec["schema"] = "spot.learning_proposal.v1"
    rec["payload_sha256"] = digest
    rec["payload_stored_path"] = str(stored)

    append_jsonl(INDEX, rec)

    print(json.dumps({
        "ok": True,
        "learning_id": learning_id,
        "correlation_id": args.correlation_id,
        "proposal_only": True,
        "auto_apply": False,
        "execution_allowed": False,
        "mutation_authority": False
    }, indent=2, sort_keys=True))

if __name__ == "__main__":
    main()
