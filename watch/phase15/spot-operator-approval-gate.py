#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path
from typing import Any


VALID_SCHEMA = "phase15.operator_approval.v1"
VALID_SCOPE = "low_risk_service_review_only"


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


def deny(root: Path, candidate: dict[str, Any], token: dict[str, Any], reason: str) -> None:
    record = {
        "schema": "phase15.approval_gate.v1",
        "ts": int(time.time()),
        "candidate_id": candidate.get("candidate_id", "unknown"),
        "approval_id": token.get("approval_id", "missing"),
        "result": "blocked",
        "block_reason": reason,
        "execution_allowed": False,
        "mutation_scope": "none",
    }
    record["record_hash"] = sha256_text(canonical(record))
    append_jsonl(root / "journals" / "phase15-denied-approvals.jsonl", record)
    raise SystemExit(f"blocked: {reason}")


def validate(root: Path, candidate: dict[str, Any], token: dict[str, Any]) -> dict[str, Any]:
    now = int(time.time())

    if not token:
        deny(root, candidate, token, "missing_approval_token")
    if token.get("schema") != VALID_SCHEMA:
        deny(root, candidate, token, "invalid_token_schema")
    if token.get("candidate_id") != candidate.get("candidate_id"):
        deny(root, candidate, token, "candidate_mismatch")
    if token.get("approved_target") != candidate.get("target"):
        deny(root, candidate, token, "target_mismatch")
    if token.get("approved_action") != candidate.get("action"):
        deny(root, candidate, token, "action_mismatch")
    if token.get("approval_scope") != VALID_SCOPE:
        deny(root, candidate, token, "scope_mismatch")
    if token.get("operator_confirmed") is not True:
        deny(root, candidate, token, "operator_confirmation_missing")
    if token.get("approved_by") != "operator":
        deny(root, candidate, token, "approver_not_operator")
    if int(token.get("expires_at", 0)) <= now:
        deny(root, candidate, token, "approval_expired")

    record = {
        "schema": "phase15.approval_gate.v1",
        "ts": now,
        "candidate_id": candidate["candidate_id"],
        "approval_id": token["approval_id"],
        "result": "accepted_for_review_handoff",
        "authority": "approval_gate_only",
        "execution_allowed": False,
        "approval_bypass_allowed": False,
        "production_mutation_allowed": False,
        "mutation_scope": "none",
    }
    record["record_hash"] = sha256_text(canonical(record))
    return record


def main() -> None:
    parser = argparse.ArgumentParser(description="Phase 15 operator approval token gate")
    parser.add_argument("--root", required=True)
    parser.add_argument("--candidate-file", required=True)
    parser.add_argument("--approval-token-file", required=True)
    args = parser.parse_args()

    root = Path(args.root)
    candidate = load_json(Path(args.candidate_file), {})
    token = load_json(Path(args.approval_token_file), {})

    record = validate(root, candidate, token)

    write_json(root / "approvals" / f"{record['approval_id']}.json", record)
    append_jsonl(root / "journals" / "phase15-accepted-approvals.jsonl", record)

    print(json.dumps(record, sort_keys=True))


if __name__ == "__main__":
    main()
