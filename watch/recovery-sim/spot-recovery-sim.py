#!/usr/bin/env python3

import argparse
import hashlib
import json
from datetime import datetime, UTC
from pathlib import Path

VALID_STATES = {
    "interrupted_rehydrate",
    "replay_denied",
    "orphan_detected",
    "stale_expired",
    "journal_chain",
}

def utc_now():
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

def sha256_text(text):
    return hashlib.sha256(text.encode()).hexdigest()

def fail(msg):
    raise SystemExit(f"[FAIL] {msg}")

def main():
    ap = argparse.ArgumentParser(description="Spot recovery orchestration simulator.")
    ap.add_argument("--mutation-sim-json", required=True)
    ap.add_argument("--state", required=True, choices=sorted(VALID_STATES))
    ap.add_argument("--out-dir", default="watch/recovery-sim/runs")
    args = ap.parse_args()

    sim_path = Path(args.mutation_sim_json)
    if not sim_path.exists():
        fail("mutation simulator artifact missing")

    sim = json.loads(sim_path.read_text())

    material = "|".join([
        sim["sim_id"],
        sim["transaction_id"],
        args.state,
    ])

    recovery_id = f"RSIM-{sha256_text(material)[:12]}"

    doc = {
        "recovery_id": recovery_id,
        "created_at": utc_now(),
        "source_sim_id": sim["sim_id"],
        "transaction_id": sim["transaction_id"],
        "state": args.state,
        "mutation_performed": False,
        "execution_performed": False,
        "rollback_performed": False,
        "recovery_required": False,
        "rehydrated": False,
        "replay_blocked": False,
        "orphan_detected": False,
        "stale_expired": False,
        "journal_chain_valid": False,
        "recovery_allowed": False,
    }

    if args.state == "interrupted_rehydrate":
        doc["recovery_required"] = True
        doc["rehydrated"] = True

    elif args.state == "replay_denied":
        doc["replay_blocked"] = True

    elif args.state == "orphan_detected":
        doc["orphan_detected"] = True

    elif args.state == "stale_expired":
        doc["stale_expired"] = True

    elif args.state == "journal_chain":
        doc["journal_chain_valid"] = True
        doc["recovery_allowed"] = True

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    out = out_dir / f"{recovery_id}.json"
    out.write_text(json.dumps(doc, indent=2) + "\n")

    print(out)

if __name__ == "__main__":
    main()
