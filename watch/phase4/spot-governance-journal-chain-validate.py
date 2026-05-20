#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
import hashlib
from pathlib import Path

SIM = Path("watch/phase4/spot-governance-journal-chain-sim.py")

EXPECTED_CASES = [
    "allowed_noop",
    "kill_switch_blocked",
    "lease_collision",
    "interrupted_before_receipt",
    "interrupted_after_receipt",
    "stale_lease_replay",
]


def require(cond: bool, msg: str) -> None:
    if not cond:
        raise SystemExit(f"[FAIL] {msg}")


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def canonical(obj: dict) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def record_hash_without_entry(record: dict) -> str:
    clone = dict(record)
    clone.pop("entry_hash", None)
    return sha256_text(canonical(clone))


def main() -> None:
    p = subprocess.run(
        [sys.executable, str(SIM)],
        text=True,
        capture_output=True,
        check=False,
    )

    require(p.returncode == 0, f"journal simulator failed: {p.stderr}")

    chain_path = Path(p.stdout.strip())
    require(chain_path.exists(), f"chain file missing: {chain_path}")

    records = []
    for line_no, line in enumerate(chain_path.read_text().splitlines(), start=1):
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError as e:
            raise SystemExit(f"[FAIL] invalid JSONL at line {line_no}: {e}")

    require(len(records) == len(EXPECTED_CASES), "unexpected journal record count")

    previous_hash = "GENESIS"
    seen_entries = set()
    seen_receipts = set()
    seen_executions = set()

    for idx, record in enumerate(records, start=1):
        expected_case = EXPECTED_CASES[idx - 1]

        require(record["journal_schema"] == "spot.phase4.governance.journal.v1", f"{expected_case}: bad schema")
        require(record["index"] == idx, f"{expected_case}: bad index")
        require(record["case"] == expected_case, f"{expected_case}: case mismatch")
        require(record["previous_hash"] == previous_hash, f"{expected_case}: broken previous_hash")
        require(record["mutation_performed"] is False, f"{expected_case}: mutation must be false")

        expected_hash = record_hash_without_entry(record)
        require(record["entry_hash"] == expected_hash, f"{expected_case}: entry hash mismatch")

        require(record["entry_hash"] not in seen_entries, f"{expected_case}: duplicate entry hash")
        require(record["receipt_id"] not in seen_receipts, f"{expected_case}: duplicate receipt")
        require(record["execution_id"] not in seen_executions, f"{expected_case}: duplicate execution")

        seen_entries.add(record["entry_hash"])
        seen_receipts.add(record["receipt_id"])
        seen_executions.add(record["execution_id"])
        previous_hash = record["entry_hash"]

    print("RESULT: PASS")
    print("journal_records=6 chain=pass tamper_detection=pass replay_detection=pass mutation=none")


if __name__ == "__main__":
    main()
