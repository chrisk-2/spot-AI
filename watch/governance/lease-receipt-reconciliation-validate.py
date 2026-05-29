#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / "watch" / "state"

SNAP = STATE / "lease-receipt-reconciliation-audit.json"
HISTORY = STATE / "lease-receipt-reconciliation-history.jsonl"

KNOWN = {
    "NONE",
    "LEASE_MISSING",
    "RECEIPT_MISSING",
    "LEASE_RECEIPT_MISMATCH",
    "CHAIN_BREAK",
    "ROLLBACK_BINDING_MISSING",
    "RECONCILIATION_MISMATCH",
}


def fail(msg: str) -> int:
    print(f"[FAIL] {msg}")
    return 1


def ok(msg: str) -> None:
    print(f"[PASS] {msg}")


def load(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def main() -> int:
    if not SNAP.exists():
        return fail("lease receipt reconciliation audit missing")

    try:
        data = load(SNAP)
    except Exception as exc:
        return fail(f"audit invalid JSON: {exc}")

    if not isinstance(data, dict):
        return fail("audit must be object")
    ok("audit valid JSON")

    if data.get("schema") != "starfleet.lease_receipt_reconciliation_audit.v1":
        return fail("schema mismatch")
    ok("schema valid")

    for key in ("execution_allowed", "mutation_authority", "live_executor_enabled"):
        if data.get(key) is not False:
            return fail(f"{key} must be false")
        ok(f"{key} false")

    if data.get("mode") != "read_only":
        return fail("mode must be read_only")
    ok("mode read_only")

    if data.get("advisory_only") is not True:
        return fail("advisory_only must be true")
    ok("advisory_only true")

    findings = data.get("findings")
    if not isinstance(findings, list) or not findings:
        return fail("findings must be non-empty list")

    for idx, finding in enumerate(findings):
        if not isinstance(finding, dict):
            return fail(f"finding[{idx}] must be object")
        cls = finding.get("classification")
        if cls not in KNOWN:
            return fail(f"finding[{idx}] unknown classification {cls}")

    ok("all classifications known")

    artifacts = data.get("artifact_summary")
    if not isinstance(artifacts, dict):
        return fail("artifact_summary must be object")
    ok("artifact summary present")

    if not HISTORY.exists():
        return fail("history missing")

    count = 0
    with HISTORY.open("r", encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except Exception as exc:
                return fail(f"history line {lineno} invalid JSON: {exc}")
            if rec.get("schema") != "starfleet.lease_receipt_reconciliation_audit.v1":
                return fail(f"history line {lineno} schema mismatch")
            count += 1

    if count < 1:
        return fail("history empty")

    ok(f"history JSONL valid count={count}")
    print("RESULT: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
