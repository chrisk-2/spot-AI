#!/usr/bin/env python3
import argparse
import json
import os
import time
import uuid
from pathlib import Path

CHAIN_INDEX = Path(os.environ.get("SPOT_CHAIN_ROOT", "/mnt/collective/logs/spot/chains")) / "index.jsonl"
LEASE_INDEX = Path(os.environ.get("SPOT_LEASE_ROOT", "/mnt/collective/logs/spot/leases")) / "index.jsonl"
ROLLBACK_INDEX = Path(os.environ.get("SPOT_ROLLBACK_ROOT", "/mnt/collective/logs/spot/rollbacks")) / "index.jsonl"
RECEIPT_WRITE = Path("watch/receipt/receipt-write.py")
ROOT = Path(os.environ.get("SPOT_NOOP_EXEC_ROOT", "/mnt/collective/logs/spot/noop-executor"))
JOURNAL = ROOT / "index.jsonl"
ARTIFACTS = ROOT / "artifacts"

def utc():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

def load_jsonl(path):
    if not path.exists():
        return []
    return [json.loads(x) for x in path.read_text().splitlines() if x.strip()]

def fail(msg):
    print(json.dumps({
        "ok": False,
        "result": "BLOCKED",
        "reason": msg,
        "execution_allowed": False,
        "mutation_authority": False
    }, indent=2, sort_keys=True))
    raise SystemExit(1)

def append(path, rec):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, sort_keys=True, separators=(",", ":")) + "\n")

def main():
    ap = argparse.ArgumentParser(description="Spot noop executor lifecycle")
    ap.add_argument("--correlation-id", required=True)
    ap.add_argument("--target", required=True)
    ap.add_argument("--action", required=True)
    args = ap.parse_args()

    cid = args.correlation_id
    chains = [r for r in load_jsonl(CHAIN_INDEX) if r.get("correlation_id") == cid]
    leases = [r for r in load_jsonl(LEASE_INDEX) if r.get("correlation_id") == cid]
    rollbacks = [r for r in load_jsonl(ROLLBACK_INDEX) if r.get("correlation_id") == cid]

    required_chain = {"review", "backup", "rollback", "apply", "governance"}
    present = {r.get("artifact_type") for r in chains}
    missing = sorted(required_chain - present)
    if missing:
        fail(f"missing required chain artifacts: {missing}")
    if not leases:
        fail("missing lease")
    if not rollbacks:
        fail("missing rollback receipt")

    for group_name, group in [("chain", chains), ("lease", leases), ("rollback", rollbacks)]:
        for r in group:
            if r.get("execution_allowed") is not False:
                fail(f"{group_name} expanded execution authority")
            if r.get("mutation_authority") is not False:
                fail(f"{group_name} expanded mutation authority")

    ts = utc()
    noop_id = f"noop-{uuid.uuid4().hex}"
    apply_attempt_id = f"apply-noop-{uuid.uuid4().hex}"

    payload = {
        "schema": "spot.noop_executor.lifecycle.v1",
        "noop_id": noop_id,
        "correlation_id": cid,
        "apply_attempt_id": apply_attempt_id,
        "target": args.target,
        "action": args.action,
        "phase": "noop",
        "ts": ts,
        "preflight_passed": True,
        "execution_performed": False,
        "mutation_performed": False,
        "rollback_required": False,
        "rollback_executed": False,
        "spot_core_executor_only": True,
        "worker_self_apply": False,
        "authority": "noop_executor_only",
        "execution_allowed": False,
        "mutation_authority": False
    }

    out = ARTIFACTS / cid
    out.mkdir(parents=True, exist_ok=True)
    stored = out / f"{ts.replace(':','')}-{noop_id}.json"
    if stored.exists():
        fail(f"refusing overwrite: {stored}")
    stored.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")

    rec = dict(payload)
    rec["payload_stored_path"] = str(stored)
    append(JOURNAL, rec)

    print(json.dumps({
        "ok": True,
        "result": "NOOP_RECORDED",
        "noop_id": noop_id,
        "correlation_id": cid,
        "apply_attempt_id": apply_attempt_id,
        "stored_path": str(stored),
        "execution_allowed": False,
        "mutation_authority": False
    }, indent=2, sort_keys=True))

if __name__ == "__main__":
    main()
