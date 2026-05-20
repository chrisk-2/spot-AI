#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path
from typing import Any


BLOCKED_TARGET_CLASSES = {
    "network",
    "firewall",
    "dns",
    "dhcp",
    "routing",
    "ssh",
    "production_database",
}

ALLOWED_TARGET_CLASS = "approved_low_risk_service"


def canonical(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    return json.loads(path.read_text())


def write_json(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, sort_keys=True) + "\n")


def append_jsonl(path: Path, obj: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, sort_keys=True) + "\n")


def evaluate(candidate: dict[str, Any]) -> tuple[str, list[str]]:
    blockers: list[str] = []

    if candidate.get("risk_class") != "low":
        blockers.append("risk_not_low")

    target_class = candidate.get("target_class")
    if target_class in BLOCKED_TARGET_CLASSES:
        blockers.append("blocked_target_class")
    elif target_class != ALLOWED_TARGET_CLASS:
        blockers.append("target_not_approved_low_risk_service")

    if candidate.get("executor") != "spot-core":
        blockers.append("executor_not_spot_core")

    if candidate.get("operator_approval_required") is not True:
        blockers.append("operator_approval_not_required")

    if candidate.get("backup_required") is not True:
        blockers.append("backup_not_required")
    if candidate.get("backup_plan_defined") is not True:
        blockers.append("backup_plan_missing")

    if candidate.get("rollback_required") is not True:
        blockers.append("rollback_not_required")
    if candidate.get("rollback_plan_defined") is not True:
        blockers.append("rollback_plan_missing")

    if candidate.get("validation_required") is not True:
        blockers.append("validation_not_required")
    if candidate.get("validation_plan_defined") is not True:
        blockers.append("validation_plan_missing")

    if candidate.get("execution_allowed") is not False:
        blockers.append("execution_authority_present")

    if candidate.get("mutation_scope") != "none":
        blockers.append("mutation_scope_not_none")

    if blockers:
        return "blocked", sorted(blockers)

    return "ready_for_operator_review", []


def build_envelope(candidate: dict[str, Any]) -> dict[str, Any]:
    readiness, blockers = evaluate(candidate)

    envelope = {
        "schema": "phase14.production_readiness_gate.v1",
        "ts": int(time.time()),
        "candidate_id": candidate.get("candidate_id", "unknown"),
        "target": candidate.get("target", "unknown"),
        "target_class": candidate.get("target_class", "unknown"),
        "risk_class": candidate.get("risk_class", "unknown"),
        "readiness": readiness,
        "blockers": blockers,
        "authority": "readiness_review_only",
        "operator_review_required": True,
        "execution_allowed": False,
        "approval_allowed": False,
        "production_mutation_allowed": False,
        "routing_change_allowed": False,
        "worker_ownership_change_allowed": False,
        "mutation_scope": "none",
    }

    envelope["envelope_hash"] = sha256_text(canonical(envelope))
    return envelope


def main() -> None:
    parser = argparse.ArgumentParser(description="Phase 14 production readiness gate")
    parser.add_argument("--root", required=True)
    parser.add_argument("--candidate-file", required=True)
    args = parser.parse_args()

    root = Path(args.root)
    candidate = load_json(Path(args.candidate_file), {})
    envelope = build_envelope(candidate)

    out = root / "envelopes" / f"{envelope['candidate_id']}.json"
    journal = root / "journals" / "phase14-production-readiness.jsonl"

    write_json(out, envelope)
    append_jsonl(journal, envelope)

    print(json.dumps(envelope, sort_keys=True))


if __name__ == "__main__":
    main()
