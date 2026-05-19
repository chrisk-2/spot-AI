#!/usr/bin/env python3

import argparse
import hashlib
import json
from datetime import datetime, UTC
from pathlib import Path

def utc_now():
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

def sha256_text(text):
    return hashlib.sha256(text.encode()).hexdigest()

def load_json(path):
    p = Path(path)
    if not p.exists():
        raise SystemExit(f"[FAIL] missing input: {path}")
    return json.loads(p.read_text())

def main():
    ap = argparse.ArgumentParser(description="Create Phase 3 dry-run proof bundle.")
    ap.add_argument("--transaction-json", required=True)
    ap.add_argument("--mutation-sim-json", required=True)
    ap.add_argument("--recovery-sim-json", required=True)
    ap.add_argument("--governance-sim-json", required=True)
    ap.add_argument("--out-dir", default="watch/phase3-proof/runs")
    args = ap.parse_args()

    tx = load_json(args.transaction_json)
    msim = load_json(args.mutation_sim_json)
    rsim = load_json(args.recovery_sim_json)
    gsim = load_json(args.governance_sim_json)

    material = "|".join([
        tx["transaction_id"],
        msim["sim_id"],
        rsim["recovery_id"],
        gsim["governance_id"],
    ])

    proof_id = f"P3PROOF-{sha256_text(material)[:12]}"

    doc = {
        "proof_id": proof_id,
        "created_at": utc_now(),
        "phase": "3.11",
        "transaction_id": tx["transaction_id"],
        "mutation_sim_id": msim["sim_id"],
        "recovery_id": rsim["recovery_id"],
        "governance_id": gsim["governance_id"],
        "mutation_performed": False,
        "execution_performed": False,
        "rollback_performed": False,
        "spot_core_sole_executor": bool(gsim.get("spot_core_sole_executor")),
        "worker_self_apply_allowed": bool(gsim.get("worker_self_apply_allowed")),
        "codex_mutation_allowed": bool(gsim.get("codex_mutation_allowed")),
        "openai_mutation_allowed": bool(gsim.get("openai_mutation_allowed")),
        "inputs": {
            "transaction": str(args.transaction_json),
            "mutation_sim": str(args.mutation_sim_json),
            "recovery_sim": str(args.recovery_sim_json),
            "governance_sim": str(args.governance_sim_json),
        },
    }

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    out = out_dir / f"{proof_id}.json"
    out.write_text(json.dumps(doc, indent=2) + "\n")
    print(out)

if __name__ == "__main__":
    main()
