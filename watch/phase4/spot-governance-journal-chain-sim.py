#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

CASES = [
    "allowed_noop",
    "kill_switch_blocked",
    "lease_collision",
    "interrupted_before_receipt",
    "interrupted_after_receipt",
    "stale_lease_replay",
]

SIM = Path("watch/phase4/spot-noop-executor-sim.py")


def utc_now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def canonical(obj: dict) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def run_receipt(case: str, out_dir: Path) -> dict:
    import subprocess
    import sys

    p = subprocess.run(
        [
            sys.executable,
            str(SIM),
            "--request-id",
            f"phase4-chain-{case}",
            "--case",
            case,
            "--out-dir",
            str(out_dir),
        ],
        text=True,
        capture_output=True,
        check=False,
    )

    if p.returncode != 0:
        raise SystemExit(f"[FAIL] simulator failed for {case}: {p.stderr}")

    receipt_path = Path(p.stdout.strip())
    return json.loads(receipt_path.read_text())


def build_chain(out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)

    previous_hash = "GENESIS"
    records = []

    for index, case in enumerate(CASES, start=1):
        receipt = run_receipt(case, out_dir)
        receipt_hash = sha256_text(canonical(receipt))

        record = {
            "journal_schema": "spot.phase4.governance.journal.v1",
            "created_at": utc_now(),
            "index": index,
            "case": case,
            "receipt_id": receipt["receipt_id"],
            "execution_id": receipt["execution_id"],
            "envelope_id": receipt["envelope_id"],
            "receipt_hash": receipt_hash,
            "previous_hash": previous_hash,
            "mutation_performed": receipt["mutation_performed"],
            "final_outcome": receipt["final_outcome"],
        }

        record["entry_hash"] = sha256_text(canonical(record))
        previous_hash = record["entry_hash"]
        records.append(record)

    chain_path = out_dir / "phase4-governance-journal-chain.jsonl"
    chain_path.write_text("\n".join(canonical(r) for r in records) + "\n")
    return chain_path


def main() -> None:
    ap = argparse.ArgumentParser(description="Phase 4 governance journal chain simulator.")
    ap.add_argument("--out-dir", default="watch/phase4/runs")
    args = ap.parse_args()

    chain_path = build_chain(Path(args.out_dir))
    print(chain_path)


if __name__ == "__main__":
    main()
