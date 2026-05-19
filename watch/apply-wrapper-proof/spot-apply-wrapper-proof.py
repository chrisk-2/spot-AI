#!/usr/bin/env python3

import argparse
import hashlib
import json
from datetime import datetime, UTC
from pathlib import Path

CASES = {
    "safe_envelope",
    "unsafe_mutation",
    "unsafe_execution",
    "unsafe_rollback",
    "executor_drift",
    "worker_self_apply",
    "codex_mutation",
    "openai_mutation",
}

REJECTION_REASON = {
    "safe_envelope": None,
    "unsafe_mutation": "unsafe_mutation",
    "unsafe_execution": "unsafe_execution",
    "unsafe_rollback": "unsafe_rollback",
    "executor_drift": "executor_drift",
    "worker_self_apply": "worker_self_apply",
    "codex_mutation": "codex_mutation",
    "openai_mutation": "openai_mutation",
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
    ap = argparse.ArgumentParser(description="Create dry-run apply-wrapper integration proof.")
    ap.add_argument("--phase3-proof-json", required=True)
    ap.add_argument("--case", required=True, choices=sorted(CASES))
    ap.add_argument("--out-dir", default="watch/apply-wrapper-proof/runs")
    args = ap.parse_args()

    proof = load_json(args.phase3_proof_json)
    reason = REJECTION_REASON[args.case]

    material = "|".join([
        proof["proof_id"],
        args.case,
    ])

    wrapper_proof_id = f"AWPROOF-{sha256_text(material)[:12]}"

    doc = {
        "wrapper_proof_id": wrapper_proof_id,
        "created_at": utc_now(),
        "phase": "3.12",
        "source_proof_id": proof["proof_id"],
        "case": args.case,
        "wrapper_allowed": args.case == "safe_envelope",
        "rejection_reason": reason,
        "mutation_performed": False,
        "execution_performed": False,
        "rollback_performed": False,
        "git_apply_performed": False,
        "service_restart_performed": False,
        "spot_core_sole_executor": proof["spot_core_sole_executor"],
        "worker_self_apply_allowed": proof["worker_self_apply_allowed"],
        "codex_mutation_allowed": proof["codex_mutation_allowed"],
        "openai_mutation_allowed": proof["openai_mutation_allowed"],
    }

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    out = out_dir / f"{wrapper_proof_id}.json"
    out.write_text(json.dumps(doc, indent=2) + "\n")
    print(out)

if __name__ == "__main__":
    main()
