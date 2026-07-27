#!/usr/bin/env python3
"""Build a non-executable Module 49 action-proposal contract."""

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any

DEFAULT_GATE_ROOT = Path(
    os.environ.get(
        "SPOT_REVIEW_GATE_ROOT",
        "/mnt/collective/logs/spot/reviews/recommendation-review-gate",
    )
)


def canonical(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
        + "\n"
    ).encode("utf-8")


def latest_gate_record(root: Path) -> Path:
    records = sorted(root.glob("*.json"))

    if not records:
        raise RuntimeError(f"no gate records found under {root}")

    return records[-1]


def load_gate(path: Path) -> tuple[dict[str, Any], str]:
    payload = path.read_bytes()
    record = json.loads(payload)

    if not isinstance(record, dict):
        raise RuntimeError("gate record must be a JSON object")

    return record, hashlib.sha256(payload).hexdigest()


def build_contract(
    gate: dict[str, Any],
    gate_path: Path,
    gate_sha256: str,
) -> dict[str, Any]:
    eligibility = gate.get("eligibility")
    if not isinstance(eligibility, dict):
        eligibility = {}

    proposal = eligibility.get("proposal")
    if not isinstance(proposal, dict):
        proposal = {}

    review = eligibility.get("review")
    if not isinstance(review, dict):
        review = {}

    ready = eligibility.get("eligible_for_next_gate") is True
    proposal_id = gate.get("proposal_id") or proposal.get("proposal_id")
    recommendation = proposal.get("top_recommendation")

    identity = {
        "source_gate_sha256": gate_sha256,
        "proposal_id": proposal_id,
        "operation_kind": "NO_OP",
        "recommendation": recommendation,
    }
    action_id = "ACT-" + hashlib.sha256(canonical(identity)).hexdigest()[:20]

    return {
        "schema_version": "1.0",
        "module": "module49_controlled_hands_noop_contract",
        "action": "ACTION_PROPOSAL",
        "mode": "no_op",
        "status": (
            "READY_FOR_NOOP_SIMULATION"
            if ready
            else "BLOCKED"
        ),
        "action_id": action_id,
        "proposal_id": proposal_id,
        "source": {
            "gate_record_path": str(gate_path),
            "gate_record_sha256": gate_sha256,
            "gate_decision": eligibility.get("decision"),
            "review_request_id": review.get("request_id"),
            "review_verdict": review.get("verdict"),
            "review_journal_path": review.get("journal_path"),
        },
        "requested_action": {
            "kind": "NO_OP",
            "recommendation": recommendation,
            "target": None,
            "argv": [],
            "shell": None,
            "executable_payload_present": False,
        },
        "lifecycle": {
            "proposal_intake": "ACCEPTED" if ready else "BLOCKED",
            "policy_gate": "ELIGIBLE" if ready else "DENIED",
            "executor_dispatch": "SUPPRESSED",
            "system_execution": "NOT_PERFORMED",
            "simulated_receipt": "NOT_CREATED",
            "next_stage": (
                "NOOP_RECEIPT_SIMULATION"
                if ready
                else None
            ),
        },
        "blockers": eligibility.get("blockers", []),
        "safety": {
            "advisory_only": True,
            "spot_core_sole_executor": True,
            "worker_self_apply": False,
            "approval_authority": False,
            "execution_allowed": False,
            "mutation_authority": False,
            "step6_authorized": False,
            "backup_created": False,
            "rollback_executed": False,
            "executor_dispatch_performed": False,
            "command_execution_performed": False,
            "mutation_performed": False,
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a read-only Controlled Hands no-op contract."
    )
    parser.add_argument("--gate-record")
    parser.add_argument("--gate-root", default=str(DEFAULT_GATE_ROOT))
    parser.add_argument("--require-ready", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    gate_path = (
        Path(args.gate_record)
        if args.gate_record
        else latest_gate_record(Path(args.gate_root))
    )

    gate, gate_sha256 = load_gate(gate_path)
    contract = build_contract(gate, gate_path, gate_sha256)

    print(json.dumps(contract, indent=2, sort_keys=True))

    if args.require_ready and contract["status"] != "READY_FOR_NOOP_SIMULATION":
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
