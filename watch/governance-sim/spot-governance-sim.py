#!/usr/bin/env python3

import argparse
import hashlib
import json
from datetime import datetime, UTC
from pathlib import Path

CASES = {
    "phase_mismatch",
    "unauthorized_role",
    "invalid_review_verdict",
    "missing_backup_binding",
    "missing_rollback_binding",
    "replayed_transaction",
    "stale_validator",
    "governance_drift",
    "clean_envelope",
}

REJECTION_REASON = {
    "phase_mismatch": "phase_mismatch",
    "unauthorized_role": "unauthorized_role",
    "invalid_review_verdict": "invalid_review_verdict",
    "missing_backup_binding": "missing_backup_binding",
    "missing_rollback_binding": "missing_rollback_binding",
    "replayed_transaction": "replayed_transaction",
    "stale_validator": "stale_validator",
    "governance_drift": "governance_drift",
    "clean_envelope": None,
}

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
    ap = argparse.ArgumentParser(description="Spot deterministic governance envelope simulator.")
    ap.add_argument("--transaction-json", required=True)
    ap.add_argument("--mutation-sim-json", required=True)
    ap.add_argument("--recovery-sim-json", required=True)
    ap.add_argument("--case", required=True, choices=sorted(CASES))
    ap.add_argument("--out-dir", default="watch/governance-sim/runs")
    args = ap.parse_args()

    tx = load_json(args.transaction_json)
    msim = load_json(args.mutation_sim_json)
    rsim = load_json(args.recovery_sim_json)

    material = "|".join([
        tx["transaction_id"],
        msim["sim_id"],
        rsim["recovery_id"],
        args.case,
    ])

    governance_id = f"GSIM-{sha256_text(material)[:12]}"
    rejection_reason = REJECTION_REASON[args.case]

    doc = {
        "governance_id": governance_id,
        "created_at": utc_now(),
        "transaction_id": tx["transaction_id"],
        "mutation_sim_id": msim["sim_id"],
        "recovery_id": rsim["recovery_id"],
        "case": args.case,
        "governance_allowed": args.case == "clean_envelope",
        "rejection_reason": rejection_reason,
        "mutation_performed": False,
        "execution_performed": False,
        "rollback_performed": False,
        "spot_core_sole_executor": True,
        "worker_self_apply_allowed": False,
        "codex_mutation_allowed": False,
        "openai_mutation_allowed": False,
    }

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    out = out_dir / f"{governance_id}.json"
    out.write_text(json.dumps(doc, indent=2) + "\n")
    print(out)

if __name__ == "__main__":
    main()
