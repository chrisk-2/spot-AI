#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
STATE_DIR = ROOT / "watch" / "state"
SNAPSHOT_PATH = STATE_DIR / "execution-state-drift.json"
HISTORY_PATH = STATE_DIR / "execution-state-drift-history.jsonl"

KNOWN_DRIFT_CLASSES = {
    "NONE",
    "LEASE_MISSING",
    "LEASE_WITHOUT_RECEIPT",
    "RECEIPT_WITHOUT_LEASE",
    "ROLLBACK_BINDING_MISSING",
    "RECONCILIATION_MISMATCH",
    "REPLAY_AUDIT_MISSING",
    "APPROVAL_STATE_MISMATCH",
    "GOVERNANCE_STATE_MISMATCH",
}

CANDIDATE_ARTIFACTS = {
    "lease_registry": [
        ROOT / "watch" / "state" / "execution-lease-registry.json",
        ROOT / "watch" / "state" / "execution-leases.json",
        ROOT / "watch" / "governance" / "runs" / "execution-lease-registry.json",
    ],
    "receipt_registry": [
        ROOT / "watch" / "state" / "execution-receipts.json",
        ROOT / "watch" / "state" / "immutable-execution-receipts.json",
        ROOT / "watch" / "governance" / "runs" / "execution-receipts.json",
    ],
    "rollback_registry": [
        ROOT / "watch" / "state" / "rollback-binding-registry.json",
        ROOT / "watch" / "state" / "rollback-bindings.json",
        ROOT / "watch" / "governance" / "runs" / "rollback-binding-registry.json",
    ],
    "approval_state": [
        ROOT / "watch" / "state" / "approval-escalation-state.json",
        ROOT / "watch" / "state" / "deterministic-approval-escalation.json",
    ],
    "transaction_reconciliation": [
        ROOT / "watch" / "state" / "transaction-state-reconciliation.json",
    ],
    "replay_audit": [
        ROOT / "watch" / "state" / "deterministic-execution-replay-audit.json",
        ROOT / "watch" / "state" / "execution-replay-audit.json",
    ],
}


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def first_existing(paths: list[Path]) -> Path | None:
    for path in paths:
        if path.exists():
            return path
    return None


def as_records(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [x for x in value if isinstance(x, dict)]
    if isinstance(value, dict):
        for key in ("records", "items", "leases", "receipts", "bindings", "events"):
            item = value.get(key)
            if isinstance(item, list):
                return [x for x in item if isinstance(x, dict)]
        return [value]
    return []


def ids_from(records: list[dict[str, Any]]) -> set[str]:
    keys = ("execution_id", "transaction_id", "lease_id", "receipt_id", "request_id", "id")
    out: set[str] = set()
    for rec in records:
        for key in keys:
            val = rec.get(key)
            if isinstance(val, str) and val.strip():
                out.add(val.strip())
                break
    return out


def artifact_summary(name: str, paths: list[Path]) -> dict[str, Any]:
    path = first_existing(paths)
    if not path:
        return {
            "name": name,
            "exists": False,
            "path": None,
            "valid_json": None,
            "record_count": 0,
            "ids": [],
            "error": None,
        }

    try:
        data = load_json(path)
        records = as_records(data)
        return {
            "name": name,
            "exists": True,
            "path": str(path.relative_to(ROOT)),
            "valid_json": True,
            "record_count": len(records),
            "ids": sorted(ids_from(records)),
            "error": None,
        }
    except Exception as exc:
        return {
            "name": name,
            "exists": True,
            "path": str(path.relative_to(ROOT)),
            "valid_json": False,
            "record_count": 0,
            "ids": [],
            "error": f"{type(exc).__name__}: {exc}",
        }


def drift_record(classification: str, message: str, severity: str = "info", **extra: Any) -> dict[str, Any]:
    return {
        "classification": classification,
        "severity": severity,
        "message": message,
        **extra,
    }


def build_snapshot() -> dict[str, Any]:
    STATE_DIR.mkdir(parents=True, exist_ok=True)

    artifacts = {
        name: artifact_summary(name, paths)
        for name, paths in CANDIDATE_ARTIFACTS.items()
    }

    drifts: list[dict[str, Any]] = []

    for name, summary in artifacts.items():
        if summary["exists"] and summary["valid_json"] is False:
            drifts.append(
                drift_record(
                    "GOVERNANCE_STATE_MISMATCH",
                    f"{name} exists but is not valid JSON",
                    "error",
                    artifact=name,
                    path=summary["path"],
                    error=summary["error"],
                )
            )

    lease_ids = set(artifacts["lease_registry"]["ids"])
    receipt_ids = set(artifacts["receipt_registry"]["ids"])
    rollback_ids = set(artifacts["rollback_registry"]["ids"])

    if receipt_ids and not lease_ids:
        drifts.append(drift_record("LEASE_MISSING", "receipt ids exist but no lease ids were found", "warn"))

    for item in sorted(lease_ids - receipt_ids):
        drifts.append(drift_record("LEASE_WITHOUT_RECEIPT", "lease id has no matching receipt id", "warn", id=item))

    for item in sorted(receipt_ids - lease_ids):
        drifts.append(drift_record("RECEIPT_WITHOUT_LEASE", "receipt id has no matching lease id", "warn", id=item))

    for item in sorted((lease_ids | receipt_ids) - rollback_ids):
        if lease_ids or receipt_ids:
            drifts.append(drift_record("ROLLBACK_BINDING_MISSING", "execution id has no matching rollback binding id", "warn", id=item))

    if not artifacts["transaction_reconciliation"]["exists"]:
        drifts.append(drift_record("RECONCILIATION_MISMATCH", "transaction reconciliation artifact not present", "info"))

    if not artifacts["replay_audit"]["exists"]:
        drifts.append(drift_record("REPLAY_AUDIT_MISSING", "execution replay audit artifact not present", "info"))

    if not artifacts["approval_state"]["exists"]:
        drifts.append(drift_record("APPROVAL_STATE_MISMATCH", "approval escalation state artifact not present", "info"))

    if not drifts:
        drifts.append(drift_record("NONE", "no execution state drift detected", "info"))

    snapshot = {
        "schema": "starfleet.execution_state_drift.v1",
        "generated_at": utc_now(),
        "mode": "read_only",
        "advisory_only": True,
        "execution_allowed": False,
        "mutation_authority": False,
        "known_drift_classes": sorted(KNOWN_DRIFT_CLASSES),
        "artifact_summary": artifacts,
        "drift_count": len([d for d in drifts if d["classification"] != "NONE"]),
        "drifts": drifts,
    }

    return snapshot


def main() -> int:
    snapshot = build_snapshot()
    tmp = SNAPSHOT_PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, SNAPSHOT_PATH)

    with HISTORY_PATH.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(snapshot, sort_keys=True) + "\n")

    print(json.dumps(snapshot, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
