#!/usr/bin/env python3
"""Validator for Module 50 lease/receipt reconciliation audit schema v2."""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
AUDIT = REPO / "watch" / "state" / "lease-receipt-reconciliation-audit.json"

EXPECTED_PROPOSAL = "THINK-20260724T165433-73e9e400daa4bbe6"
EXPECTED_ACTION = "ACT-ba58a8dd0ce1a62f88e9"

SAFE_CONTEXT_CLASSES = {
    "READ_ONLY_CONTEXT",
    "BLOCKED_PREFLIGHT_CONTEXT",
    "SIMULATED_NOOP_CONTEXT",
    "SANDBOX_ONLY_CONTEXT",
    "OBSERVATIONAL_LIFE_PULSE_CONTEXT",
}


def require(condition: bool, message: str, failures: list[str]) -> None:
    if condition:
        print(f"[PASS] {message}")
    else:
        print(f"[FAIL] {message}")
        failures.append(message)


def main() -> int:
    failures: list[str] = []

    require(AUDIT.is_file(), f"audit artifact exists: {AUDIT}", failures)
    if failures:
        return 1

    try:
        record = json.loads(AUDIT.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        print(f"[FAIL] unreadable audit artifact: {error}")
        return 1

    governance = record.get("governance", {})
    evidence = record.get("execution_evidence", {})
    context = record.get("non_live_context_evidence", {})
    boundary = record.get("safety_boundary", {})
    artifacts = context.get("artifacts", [])

    require(record.get("schema_version") == "v2", "schema_version=v2", failures)
    require(record.get("proposal_id") == EXPECTED_PROPOSAL, "proposal identity matches", failures)
    require(record.get("action_id") == EXPECTED_ACTION, "action identity matches", failures)
    require(
        record.get("primary_classification") == "BLOCKED_NO_EXECUTION_EVIDENCE",
        "primary classification is BLOCKED_NO_EXECUTION_EVIDENCE",
        failures,
    )
    require(record.get("result") == "PASS", "audit result is PASS", failures)
    require(evidence.get("present") is False, "no qualifying execution evidence", failures)
    require(evidence.get("count") == 0, "qualifying evidence count is zero", failures)
    require(evidence.get("paths") == [], "qualifying evidence paths are empty", failures)
    require(isinstance(artifacts, list), "non-live context artifacts are listed", failures)
    require(
        context.get("present") is bool(artifacts)
        and context.get("count") == len(artifacts),
        "non-live context summary is consistent",
        failures,
    )
    require(
        all(
            isinstance(artifact, dict)
            and artifact.get("classification") in SAFE_CONTEXT_CLASSES
            for artifact in artifacts
        ),
        "all context artifacts are explicitly non-live",
        failures,
    )
    require(governance.get("execution_allowed") is False, "execution_allowed=false", failures)
    require(governance.get("mutation_authority") is False, "mutation_authority=false", failures)
    require(governance.get("step6_authorized") is False, "step6_authorized=false", failures)
    require(governance.get("live_executor_enabled") is False, "live_executor_enabled=false", failures)

    for key, value in boundary.items():
        require(value is False, f"safety boundary preserved: {key}=false", failures)

    if failures:
        print(f"RESULT: FAIL ({len(failures)} check(s))")
        return 1

    print("RESULT: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
