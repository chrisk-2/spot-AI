#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
STATE = ROOT / "watch" / "state"

OUT = STATE / "lease-receipt-reconciliation-audit.json"
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

ARTIFACTS = {
    "execution_state_drift": STATE / "execution-state-drift.json",
    "noop_executor_lifecycle": STATE / "noop-executor-lifecycle.json",
    "execution_reconciliation": STATE / "execution-reconciliation-journal.json",
    "execution_lease_registry": STATE / "execution-lease-registry.json",
    "execution_receipt_registry": STATE / "execution-receipts.json",
    "lease_receipt_chain": STATE / "lease-receipt-chain.json",
    "rollback_binding_registry": STATE / "rollback-binding-registry.json",
}


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_json(path: Path) -> tuple[bool, dict[str, Any] | list[Any] | None, str | None]:
    if not path.exists():
        return False, None, None
    try:
        with path.open("r", encoding="utf-8") as fh:
            return True, json.load(fh), None
    except Exception as exc:
        return True, None, f"{type(exc).__name__}: {exc}"


def records(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]
    if isinstance(data, dict):
        for key in ("records", "items", "leases", "receipts", "bindings", "chain", "events"):
            val = data.get(key)
            if isinstance(val, list):
                return [x for x in val if isinstance(x, dict)]
        return [data]
    return []


def ids(data: Any) -> set[str]:
    out: set[str] = set()
    for rec in records(data):
        for key in ("execution_id", "transaction_id", "lease_id", "receipt_id", "request_id", "id"):
            val = rec.get(key)
            if isinstance(val, str) and val.strip():
                out.add(val.strip())
                break
    return out


def artifact_status() -> dict[str, dict[str, Any]]:
    result = {}
    for name, path in ARTIFACTS.items():
        present, data, error = load_json(path)
        result[name] = {
            "present": present,
            "path": str(path.relative_to(ROOT)),
            "valid_json": error is None if present else None,
            "schema": data.get("schema") if isinstance(data, dict) else None,
            "generated_at": data.get("generated_at") if isinstance(data, dict) else None,
            "record_count": len(records(data)),
            "ids": sorted(ids(data)),
            "error": error,
        }
    return result


def audit_record(classification: str, message: str, severity: str = "info", **extra: Any) -> dict[str, Any]:
    return {
        "classification": classification,
        "severity": severity,
        "message": message,
        **extra,
    }


def build() -> dict[str, Any]:
    STATE.mkdir(parents=True, exist_ok=True)

    artifacts = artifact_status()
    findings: list[dict[str, Any]] = []

    for name, info in artifacts.items():
        if info["present"] and info["valid_json"] is False:
            findings.append(audit_record("RECONCILIATION_MISMATCH", f"{name} exists but is invalid JSON", "error", artifact=name, error=info["error"]))

    lease_ids = set(artifacts["execution_lease_registry"]["ids"])
    receipt_ids = set(artifacts["execution_receipt_registry"]["ids"])
    chain_ids = set(artifacts["lease_receipt_chain"]["ids"])
    rollback_ids = set(artifacts["rollback_binding_registry"]["ids"])

    if receipt_ids and not lease_ids:
        findings.append(audit_record("LEASE_MISSING", "receipt ids exist but no lease ids exist", "warn"))

    if lease_ids and not receipt_ids:
        findings.append(audit_record("RECEIPT_MISSING", "lease ids exist but no receipt ids exist", "warn"))

    for item in sorted(lease_ids - receipt_ids):
        findings.append(audit_record("LEASE_RECEIPT_MISMATCH", "lease id has no matching receipt id", "warn", id=item))

    for item in sorted(receipt_ids - lease_ids):
        findings.append(audit_record("LEASE_RECEIPT_MISMATCH", "receipt id has no matching lease id", "warn", id=item))

    if chain_ids:
        for item in sorted((lease_ids | receipt_ids) - chain_ids):
            findings.append(audit_record("CHAIN_BREAK", "execution id missing from lease receipt chain", "warn", id=item))

    if rollback_ids:
        for item in sorted((lease_ids | receipt_ids | chain_ids) - rollback_ids):
            findings.append(audit_record("ROLLBACK_BINDING_MISSING", "execution id missing rollback binding", "warn", id=item))

    required_context = [
        "execution_state_drift",
        "noop_executor_lifecycle",
        "execution_reconciliation",
    ]

    for name in required_context:
        if not artifacts[name]["present"]:
            findings.append(audit_record("RECONCILIATION_MISMATCH", f"required context artifact missing: {name}", "warn", artifact=name))

    if not findings:
        findings.append(audit_record("NONE", "lease receipt reconciliation audit found no mismatches", "info"))

    return {
        "schema": "starfleet.lease_receipt_reconciliation_audit.v1",
        "generated_at": now(),
        "mode": "read_only",
        "advisory_only": True,
        "execution_allowed": False,
        "mutation_authority": False,
        "live_executor_enabled": False,
        "known_classifications": sorted(KNOWN),
        "artifact_summary": artifacts,
        "finding_count": len([x for x in findings if x["classification"] != "NONE"]),
        "findings": findings,
    }


def main() -> int:
    snapshot = build()
    tmp = OUT.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, OUT)

    with HISTORY.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(snapshot, sort_keys=True) + "\n")

    print(json.dumps(snapshot, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
