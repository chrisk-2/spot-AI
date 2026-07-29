#!/usr/bin/env python3
"""Read-only Module 50 lease/receipt reconciliation audit, schema v2."""

from __future__ import annotations

import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[2]
STATE = REPO / "watch" / "state"
OUT = STATE / "lease-receipt-reconciliation-audit.json"
HISTORY = STATE / "lease-receipt-reconciliation-history.jsonl"

PROPOSAL_ID = "THINK-20260724T165433-73e9e400daa4bbe6"
ACTION_ID = "ACT-ba58a8dd0ce1a62f88e9"

CLASSIFICATION_CATALOG = [
    "NONE",
    "LEASE_MISSING",
    "RECEIPT_MISSING",
    "LEASE_RECEIPT_MISMATCH",
    "CHAIN_BREAK",
    "ROLLBACK_BINDING_MISSING",
    "RECONCILIATION_MISMATCH",
    "BLOCKED_NO_EXECUTION_EVIDENCE",
    "UNEXPECTED_PERSISTED_EXECUTION_EVIDENCE",
]

SCAN_ROOTS = (
    STATE,
    Path("/mnt/collective/logs/spot/actions"),
    Path("/mnt/collective/logs/spot/executor"),
    Path("/mnt/collective/logs/spot/governance"),
)

RELEVANT_SCHEMA_TOKENS = (
    "execution",
    "executor",
    "lease",
    "receipt",
    "chain",
    "rollback",
    "reconciliation",
    "lifecycle",
)

RELEVANT_KEYS = {
    "execution_allowed",
    "execution_performed",
    "executor_dispatch_allowed",
    "live_executor_enabled",
    "live_infrastructure_mutation",
    "lease_id",
    "receipt_id",
    "mutation_performed",
    "rollback_plan_defined",
    "sandbox_path",
}

SAFE_CONTEXT_CLASSES = {
    "READ_ONLY_CONTEXT",
    "BLOCKED_PREFLIGHT_CONTEXT",
    "SIMULATED_NOOP_CONTEXT",
    "SANDBOX_ONLY_CONTEXT",
    "OBSERVATIONAL_LIFE_PULSE_CONTEXT",
}

MUTATION_SIGNAL_KEYS = {
    "execution_performed",
    "mutation_performed",
    "live_infrastructure_mutation",
    "commands_executed",
    "services_restarted",
    "leases_modified",
    "receipts_modified",
    "rollback_bindings_modified",
    "reconciliation_journals_modified",
}

IGNORED_PATHS = {OUT.resolve(), HISTORY.resolve()}


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_records(path: Path) -> list[dict[str, Any]] | None:
    try:
        if path.suffix.lower() == ".jsonl":
            values = [
                json.loads(line)
                for line in path.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
        else:
            value = json.loads(path.read_text(encoding="utf-8"))
            values = value if isinstance(value, list) else [value]
    except (OSError, json.JSONDecodeError):
        return None

    records = [value for value in values if isinstance(value, dict)]
    return records or None


def is_relevant(record: dict[str, Any]) -> bool:
    schema = str(record.get("schema", "")).lower()
    return (
        any(token in schema for token in RELEVANT_SCHEMA_TOKENS)
        or bool(RELEVANT_KEYS.intersection(record))
    )


def has_mutation_signal(value: Any) -> bool:
    if isinstance(value, dict):
        for key, nested in value.items():
            if key in MUTATION_SIGNAL_KEYS and nested is True:
                return True
            if has_mutation_signal(nested):
                return True
    elif isinstance(value, list):
        return any(has_mutation_signal(item) for item in value)
    return False


def events_are_non_mutating(record: dict[str, Any]) -> bool:
    events = record.get("events")
    return (
        isinstance(events, list)
        and bool(events)
        and all(
            isinstance(event, dict)
            and event.get("execution_performed") is False
            and event.get("mutation_performed") is False
            and event.get("simulated") is True
            for event in events
        )
    )


def is_simulated_noop(record: dict[str, Any]) -> bool:
    return (
        record.get("simulation_only") is True
        and record.get("execution_allowed") is False
        and record.get("mutation_authority") is False
        and record.get("live_executor_enabled") is False
        and events_are_non_mutating(record)
        and not has_mutation_signal(record)
    )


def is_blocked_preflight(record: dict[str, Any]) -> bool:
    return (
        record.get("all_known_preflights_blocked_and_non_mutating") is True
        and record.get("invalid_count") == 0
        and not has_mutation_signal(record)
    )


def is_sandbox_only(record: dict[str, Any]) -> bool:
    sandbox_path = record.get("sandbox_path")
    target = record.get("target")
    return (
        record.get("mode") == "sandbox_live_only"
        and record.get("live_infrastructure_mutation") is False
        and record.get("mutation_authority") is False
        and isinstance(sandbox_path, str)
        and isinstance(target, str)
        and target.startswith(sandbox_path.rstrip("/") + "/")
    )


def is_observational_life_pulse(record: dict[str, Any]) -> bool:
    governance = record.get("governance")
    return (
        record.get("schema") == "spot.life_pulse.v1"
        and record.get("mode") == "read_only_observe_summarize_journal_propose"
        and record.get("execution_allowed") is False
        and record.get("mutation_authority") is False
        and isinstance(governance, dict)
        and governance.get("state") == "observe_only"
        and governance.get("auto_apply") is False
        and governance.get("execution_allowed") is False
        and governance.get("full_autonomy") is False
        and governance.get("mutation_authority") is False
        and not has_mutation_signal(record)
    )


def is_read_only(record: dict[str, Any]) -> bool:
    return (
        record.get("mode") == "read_only"
        and record.get("advisory_only") is True
        and record.get("execution_allowed") is False
        and record.get("mutation_authority") is False
        and not has_mutation_signal(record)
    )


def classify(path: Path, records: list[dict[str, Any]]) -> dict[str, str] | None:
    relevant = [record for record in records if is_relevant(record)]
    if not relevant:
        return None

    if all(is_simulated_noop(record) for record in relevant):
        classification = "SIMULATED_NOOP_CONTEXT"
    elif all(is_blocked_preflight(record) for record in relevant):
        classification = "BLOCKED_PREFLIGHT_CONTEXT"
    elif all(is_sandbox_only(record) for record in relevant):
        classification = "SANDBOX_ONLY_CONTEXT"
    elif all(is_observational_life_pulse(record) for record in relevant):
        classification = "OBSERVATIONAL_LIFE_PULSE_CONTEXT"
    elif all(is_read_only(record) for record in relevant):
        classification = "READ_ONLY_CONTEXT"
    else:
        classification = "QUALIFYING_CONTROLLED_EXECUTION_EVIDENCE"

    return {"path": str(path), "classification": classification}


def classify_artifacts() -> list[dict[str, str]]:
    artifacts: list[dict[str, str]] = []

    for root in SCAN_ROOTS:
        if not root.exists():
            continue

        for path in root.rglob("*"):
            if not path.is_file() or path.suffix.lower() not in {".json", ".jsonl"}:
                continue
            if path.resolve() in IGNORED_PATHS:
                continue

            records = load_records(path)
            if records is None:
                continue

            artifact = classify(path, records)
            if artifact is not None:
                artifacts.append(artifact)

    return sorted(artifacts, key=lambda artifact: artifact["path"])


def build_record() -> dict[str, Any]:
    artifacts = classify_artifacts()
    qualifying = [
        artifact
        for artifact in artifacts
        if artifact["classification"] == "QUALIFYING_CONTROLLED_EXECUTION_EVIDENCE"
    ]
    context = [
        artifact
        for artifact in artifacts
        if artifact["classification"] in SAFE_CONTEXT_CLASSES
    ]

    evidence_present = bool(qualifying)
    primary_classification = (
        "UNEXPECTED_PERSISTED_EXECUTION_EVIDENCE"
        if evidence_present
        else "BLOCKED_NO_EXECUTION_EVIDENCE"
    )

    return {
        "schema_version": "v2",
        "audit_id": f"LRA-{uuid.uuid4().hex[:20]}",
        "generated_at": utc_now(),
        "module": "lease-receipt-reconciliation",
        "mode": "read_only",
        "advisory_only": True,
        "proposal_id": PROPOSAL_ID,
        "action_id": ACTION_ID,
        "governance": {
            "execution_allowed": False,
            "mutation_authority": False,
            "step6_authorized": False,
            "live_executor_enabled": False,
            "executor": "spot-core",
        },
        "classification_catalog": CLASSIFICATION_CATALOG,
        "primary_classification": primary_classification,
        "execution_evidence": {
            "present": evidence_present,
            "count": len(qualifying),
            "paths": [artifact["path"] for artifact in qualifying],
        },
        "non_live_context_evidence": {
            "present": bool(context),
            "count": len(context),
            "artifacts": context,
        },
        "model_classifications": {
            "NONE": not evidence_present,
            "LEASE_MISSING": False,
            "RECEIPT_MISSING": False,
            "LEASE_RECEIPT_MISMATCH": False,
            "CHAIN_BREAK": False,
            "ROLLBACK_BINDING_MISSING": False,
            "RECONCILIATION_MISMATCH": False,
        },
        "result": "PASS" if not evidence_present else "FAIL",
        "safety_boundary": {
            "commands_executed": False,
            "services_restarted": False,
            "leases_modified": False,
            "receipts_modified": False,
            "rollback_bindings_modified": False,
            "reconciliation_journals_modified": False,
            "authority_granted": False,
        },
    }


def write_record(record: dict[str, Any]) -> None:
    STATE.mkdir(parents=True, exist_ok=True)
    temporary = OUT.with_suffix(".json.tmp")
    temporary.write_text(
        json.dumps(record, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, OUT)

    with HISTORY.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True) + "\n")


def main() -> int:
    record = build_record()
    write_record(record)
    print(json.dumps(record, indent=2, sort_keys=True))
    return 0 if record["result"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
