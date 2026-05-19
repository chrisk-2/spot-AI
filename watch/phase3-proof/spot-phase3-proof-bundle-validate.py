#!/usr/bin/env python3

import argparse
import json
from pathlib import Path

REQUIRED = {
    "proof_id",
    "created_at",
    "phase",
    "transaction_id",
    "mutation_sim_id",
    "recovery_id",
    "governance_id",
    "mutation_performed",
    "execution_performed",
    "rollback_performed",
    "spot_core_sole_executor",
    "worker_self_apply_allowed",
    "codex_mutation_allowed",
    "openai_mutation_allowed",
    "inputs",
}

def fail(msg):
    raise SystemExit(f"[FAIL] {msg}")

def main():
    ap = argparse.ArgumentParser(description="Validate Phase 3 proof bundle.")
    ap.add_argument("--file", required=True)
    args = ap.parse_args()

    p = Path(args.file)
    if not p.exists():
        fail("proof bundle missing")

    data = json.loads(p.read_text())
    missing = REQUIRED - set(data)
    if missing:
        fail(f"missing fields: {sorted(missing)}")

    if data["phase"] != "3.11":
        fail("phase must be 3.11")

    if data["mutation_performed"] is not False:
        fail("mutation_performed must remain false")
    if data["execution_performed"] is not False:
        fail("execution_performed must remain false")
    if data["rollback_performed"] is not False:
        fail("rollback_performed must remain false")

    if data["spot_core_sole_executor"] is not True:
        fail("Spot Core sole executor invariant failed")
    if data["worker_self_apply_allowed"] is not False:
        fail("worker self-apply must remain blocked")
    if data["codex_mutation_allowed"] is not False:
        fail("Codex mutation must remain blocked")
    if data["openai_mutation_allowed"] is not False:
        fail("OpenAI mutation must remain blocked")

    print(f"[PASS] Phase 3 proof bundle valid: {p}")

if __name__ == "__main__":
    main()
