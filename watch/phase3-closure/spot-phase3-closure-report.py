#!/usr/bin/env python3

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, UTC
from pathlib import Path

def utc_now():
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

def sha256_text(text):
    return hashlib.sha256(text.encode()).hexdigest()

def run(cmd):
    return subprocess.check_output(cmd, text=True).strip()

def load_json(path):
    p = Path(path)
    if not p.exists():
        raise SystemExit(f"[FAIL] missing input: {path}")
    return json.loads(p.read_text())

def main():
    ap = argparse.ArgumentParser(description="Create Phase 3 dry-run chain closure report.")
    ap.add_argument("--phase3-proof-json", required=True)
    ap.add_argument("--apply-wrapper-proof-json", required=True)
    ap.add_argument("--out-dir", default="watch/phase3-closure/runs")
    args = ap.parse_args()

    p3 = load_json(args.phase3_proof_json)
    aw = load_json(args.apply_wrapper_proof_json)

    head = run(["git", "rev-parse", "--short", "HEAD"])
    branch = run(["git", "branch", "--show-current"])

    material = "|".join([
        head,
        p3["proof_id"],
        aw["wrapper_proof_id"],
    ])

    closure_id = f"P3CLOSE-{sha256_text(material)[:12]}"

    doc = {
        "closure_id": closure_id,
        "created_at": utc_now(),
        "phase": "3.13",
        "branch": branch,
        "head": head,
        "phase3_proof_id": p3["proof_id"],
        "apply_wrapper_proof_id": aw["wrapper_proof_id"],
        "validation_expected": {
            "pass": 30,
            "warn": 0,
            "fail": 0,
        },
        "mutation_performed": False,
        "execution_performed": False,
        "rollback_performed": False,
        "git_apply_enabled": False,
        "config_mutation_enabled": False,
        "service_restart_enabled": False,
        "rollback_restore_enabled": False,
        "spot_core_sole_executor": True,
        "worker_self_apply_allowed": False,
        "codex_mutation_allowed": False,
        "openai_mutation_allowed": False,
        "next_live_gate_recommendation": "design_review_only_for_first_controlled_noop_executor_integration",
        "inputs": {
            "phase3_proof": str(args.phase3_proof_json),
            "apply_wrapper_proof": str(args.apply_wrapper_proof_json),
        },
    }

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    out = out_dir / f"{closure_id}.json"
    out.write_text(json.dumps(doc, indent=2) + "\n")
    print(out)

if __name__ == "__main__":
    main()
