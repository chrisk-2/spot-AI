#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path
from typing import Any


REQUIRED_PROOFS = {
    "phase7_readonly_observation",
    "phase8_dryrun_planning",
    "phase9_lowrisk_wrapper",
    "phase10_rollback_integrated",
    "phase11_supervised_chain",
    "phase12_advisory_learning",
}


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


def evaluate_proofs(proofs: dict[str, Any]) -> tuple[str, list[str], list[str]]:
    missing = sorted(REQUIRED_PROOFS - set(proofs))
    failed = sorted([
        name
        for name, proof in proofs.items()
        if name in REQUIRED_PROOFS and proof.get("result") != "pass"
    ])

    if missing:
        return "blocked_missing_proof", missing, failed
    if failed:
        return "blocked_failed_proof", missing, failed
    return "ready_for_operator_review", missing, failed


def build_envelope(input_data: dict[str, Any]) -> dict[str, Any]:
    proofs = input_data.get("proofs", {})
    readiness, missing, failed = evaluate_proofs(proofs)

    recommendations = [
        "continue_supervised_only",
        "require_operator_review_before_any_live_scope",
        "preserve_spot_core_sole_executor",
        "preserve_backup_and_rollback_gates",
    ]

    if readiness != "ready_for_operator_review":
        recommendations.append("do_not_advance_phase")

    envelope = {
        "schema": "phase13.operational_intelligence.v1",
        "ts": int(time.time()),
        "fabric_id": input_data.get("fabric_id", "phase13-fabric"),
        "readiness": readiness,
        "missing_proofs": missing,
        "failed_proofs": failed,
        "proof_count": len(proofs),
        "required_proof_count": len(REQUIRED_PROOFS),
        "recommendations": recommendations,
        "authority": "advisory_only",
        "execution_allowed": False,
        "approval_allowed": False,
        "routing_change_allowed": False,
        "worker_ownership_change_allowed": False,
        "production_mutation_allowed": False,
        "mutation_scope": "none",
    }

    envelope["envelope_hash"] = sha256_text(canonical(envelope))
    return envelope


def main() -> None:
    parser = argparse.ArgumentParser(description="Phase 13 supervised operational intelligence fabric")
    parser.add_argument("--root", required=True)
    parser.add_argument("--input-file", required=True)
    args = parser.parse_args()

    root = Path(args.root)
    input_data = load_json(Path(args.input_file), {})
    envelope = build_envelope(input_data)

    out = root / "envelopes" / f"{envelope['fabric_id']}.json"
    journal = root / "journals" / "phase13-operational-intelligence.jsonl"

    write_json(out, envelope)
    append_jsonl(journal, envelope)

    print(json.dumps(envelope, sort_keys=True))


if __name__ == "__main__":
    main()
