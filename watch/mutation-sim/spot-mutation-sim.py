#!/usr/bin/env python3

import argparse
import hashlib
import json
from datetime import datetime, UTC
from pathlib import Path

VALID_STATES = {
    "staged_apply",
    "validation_failure",
    "rollback_transition",
    "interrupted_transaction",
    "replay_collision",
}

def utc_now():
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

def sha256_text(text):
    return hashlib.sha256(text.encode()).hexdigest()

def fail(msg):
    raise SystemExit(f"[FAIL] {msg}")

def main():
    ap = argparse.ArgumentParser(description="Spot mutation lifecycle simulator.")
    ap.add_argument("--transaction-json", required=True)
    ap.add_argument("--state", required=True, choices=sorted(VALID_STATES))
    ap.add_argument("--out-dir", default="watch/mutation-sim/runs")

    args = ap.parse_args()

    tx_path = Path(args.transaction_json)

    if not tx_path.exists():
        fail("transaction json missing")

    tx = json.loads(tx_path.read_text())

    material = "|".join([
        tx["transaction_id"],
        args.state,
    ])

    sim_id = f"SIM-{sha256_text(material)[:12]}"

    doc = {
        "sim_id": sim_id,
        "created_at": utc_now(),
        "transaction_id": tx["transaction_id"],
        "state": args.state,
        "mutation_performed": False,
        "execution_performed": False,
        "rollback_performed": False,
        "rollback_simulated": False,
        "rollback_required": False,
        "recovery_required": False,
        "replay_blocked": False,
    }

    if args.state == "validation_failure":
        doc["rollback_required"] = True

    elif args.state == "rollback_transition":
        doc["rollback_required"] = True
        doc["rollback_simulated"] = True

    elif args.state == "interrupted_transaction":
        doc["recovery_required"] = True

    elif args.state == "replay_collision":
        doc["replay_blocked"] = True

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    out = out_dir / f"{sim_id}.json"
    out.write_text(json.dumps(doc, indent=2) + "\n")

    print(out)

if __name__ == "__main__":
    main()
