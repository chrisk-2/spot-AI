#!/usr/bin/env python3
import argparse
import json
import os
import time
import uuid
from pathlib import Path

ROOT = Path(os.environ.get("SPOT_ACCEPTANCE_ROOT", "/mnt/collective/logs/spot/acceptance"))
INDEX = ROOT / "index.jsonl"
ARTIFACTS = ROOT / "artifacts"

SOURCES = {
    "chain": Path(os.environ.get("SPOT_CHAIN_ROOT", "/mnt/collective/logs/spot/chains")) / "index.jsonl",
    "receipt": Path(os.environ.get("SPOT_RECEIPT_ROOT", "/mnt/collective/logs/spot/receipts")) / "index.jsonl",
    "lease": Path(os.environ.get("SPOT_LEASE_ROOT", "/mnt/collective/logs/spot/leases")) / "index.jsonl",
    "rollback": Path(os.environ.get("SPOT_ROLLBACK_ROOT", "/mnt/collective/logs/spot/rollbacks")) / "index.jsonl",
    "noop": Path(os.environ.get("SPOT_NOOP_EXEC_ROOT", "/mnt/collective/logs/spot/noop-executor")) / "index.jsonl",
    "bundle": Path(os.environ.get("SPOT_GOVERNANCE_BUNDLE_ROOT", "/mnt/collective/logs/spot/governance-bundles")) / "index.jsonl",
    "approval": Path(os.environ.get("SPOT_APPROVAL_ROOT", "/mnt/collective/logs/spot/approvals")) / "index.jsonl",
    "failure": Path(os.environ.get("SPOT_FAILURE_ROOT", "/mnt/collective/logs/spot/failure-proofs")) / "index.jsonl",
    "sandbox": Path(os.environ.get("SPOT_SANDBOX_ROOT", "/mnt/collective/logs/spot/sandbox-mutation")) / "index.jsonl",
    "remediation": Path(os.environ.get("SPOT_REMEDIATION_ROOT", "/mnt/collective/logs/spot/controlled-remediation")) / "index.jsonl",
    "rollback_failure": Path(os.environ.get("SPOT_REMEDIATION_ROOT", "/mnt/collective/logs/spot/controlled-remediation")) / "rollback-index.jsonl",
    "learning": Path(os.environ.get("SPOT_LEARNING_ROOT", "/mnt/collective/logs/spot/learning")) / "index.jsonl"
}

def utc():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

def load(path):
    if not path.exists():
        return []
    return [json.loads(x) for x in path.read_text().splitlines() if x.strip()]

def append_jsonl(path, rec):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, sort_keys=True, separators=(",", ":")) + "\n")

def fail(msg):
    print(json.dumps({
        "ok": False,
        "decision": "NO",
        "reason": msg,
        "execution_allowed": False,
        "mutation_authority": False
    }, indent=2, sort_keys=True))
    raise SystemExit(1)

def main():
    ap = argparse.ArgumentParser(description="Controlled autonomy acceptance aggregation")
    ap.add_argument("--correlation-id", required=True)
    args = ap.parse_args()

    acceptance_id = f"acceptance-{uuid.uuid4().hex}"
    ts = utc()

    counts = {name: len(load(path)) for name, path in SOURCES.items()}

    required = {
        "chain",
        "receipt",
        "lease",
        "rollback",
        "noop",
        "bundle",
        "approval",
        "failure",
        "sandbox",
        "remediation",
        "rollback_failure",
        "learning"
    }

    missing = sorted([name for name in required if counts.get(name, 0) < 1])
    if missing:
        fail(f"missing required evidence classes: {missing}")

    rec = {
        "schema": "spot.controlled_autonomy_acceptance.v1",
        "acceptance_id": acceptance_id,
        "correlation_id": args.correlation_id,
        "ts": ts,
        "counts": counts,
        "decision": "PASS",
        "controlled_autonomy_ready": True,
        "live_production_mutation_authorized": False,
        "proposal_only_learning": True,
        "spot_core_executor_only": True,
        "worker_self_apply": False,
        "execution_allowed": False,
        "mutation_authority": False,
        "authority": "acceptance_gate_only"
    }

    out = ARTIFACTS / args.correlation_id
    out.mkdir(parents=True, exist_ok=True)

    receipt = out / f"{ts.replace(':','')}-{acceptance_id}.json"
    receipt.write_text(json.dumps(rec, indent=2, sort_keys=True), encoding="utf-8")

    rec["receipt_path"] = str(receipt)

    append_jsonl(INDEX, rec)

    print(json.dumps({
        "ok": True,
        "acceptance_id": acceptance_id,
        "decision": "PASS",
        "controlled_autonomy_ready": True,
        "live_production_mutation_authorized": False,
        "execution_allowed": False,
        "mutation_authority": False
    }, indent=2, sort_keys=True))

if __name__ == "__main__":
    main()
