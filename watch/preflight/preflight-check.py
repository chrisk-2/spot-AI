#!/usr/bin/env python3
import argparse, json, os
from pathlib import Path

CHAIN = Path(os.environ.get("SPOT_CHAIN_ROOT", "/mnt/collective/logs/spot/chains")) / "index.jsonl"
LEASE = Path(os.environ.get("SPOT_LEASE_ROOT", "/mnt/collective/logs/spot/leases")) / "index.jsonl"
ROLLBACK = Path(os.environ.get("SPOT_ROLLBACK_ROOT", "/mnt/collective/logs/spot/rollbacks")) / "index.jsonl"
RECEIPT = Path(os.environ.get("SPOT_RECEIPT_ROOT", "/mnt/collective/logs/spot/receipts")) / "index.jsonl"

def load(path):
    if not path.exists():
        return []
    return [json.loads(x) for x in path.read_text().splitlines() if x.strip()]

def fail(m):
    print(json.dumps({"ok": False, "preflight": "FAIL", "reason": m, "execution_allowed": False, "mutation_authority": False}, indent=2, sort_keys=True))
    raise SystemExit(1)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--correlation-id", required=True)
    args = ap.parse_args()
    cid = args.correlation_id

    chains = [r for r in load(CHAIN) if r.get("correlation_id") == cid]
    leases = [r for r in load(LEASE) if r.get("correlation_id") == cid]
    rollbacks = [r for r in load(ROLLBACK) if r.get("correlation_id") == cid]
    receipts = [r for r in load(RECEIPT) if r.get("correlation_id") == cid]

    types = {r.get("artifact_type") for r in chains}
    required_chain = {"review", "backup", "rollback", "apply", "governance"}
    missing = sorted(required_chain - types)
    if missing:
        fail(f"missing chain artifact types: {missing}")
    if not leases:
        fail("missing execution lease")
    if not rollbacks:
        fail("missing rollback receipt")
    if not receipts:
        fail("missing execution receipt")

    for group_name, group in [("chain", chains), ("lease", leases), ("rollback", rollbacks), ("receipt", receipts)]:
        for r in group:
            if r.get("execution_allowed") is not False:
                fail(f"{group_name} expands execution authority")
            if r.get("mutation_authority") is not False:
                fail(f"{group_name} expands mutation authority")

    print(json.dumps({
        "ok": True,
        "preflight": "PASS",
        "correlation_id": cid,
        "chain_entries": len(chains),
        "lease_entries": len(leases),
        "rollback_entries": len(rollbacks),
        "receipt_entries": len(receipts),
        "execution_allowed": False,
        "mutation_authority": False
    }, indent=2, sort_keys=True))
if __name__ == "__main__":
    main()
