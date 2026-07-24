#!/usr/bin/env python3
"""Fail-closed Module 47 recommendation review eligibility evaluator.

This program only reads a captured Thinking Loop status, an optional immutable
review journal, and existing governance contract validators. It never requests
a review, writes a journal, dispatches an executor, or authorizes mutation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]

CONTRACT_VALIDATORS = {
    "approved_remediation_plan":
        "watch/remediation/approved-remediation-plan-validate.py",
    "approval_escalation":
        "watch/approval/approval-escalation-chain-validate.py",
    "execution_lease":
        "watch/executor/execution-lease-validate.py",
    "execution_quorum":
        "watch/executor/execution-quorum-validate.py",
    "execution_receipt":
        "watch/executor/execution-receipt-registry-validate.py",
    "execution_replay_audit":
        "watch/executor/execution-replay-audit-validate.py",
    "lease_receipt_chain":
        "watch/executor/lease-receipt-chain-validate.py",
    "replay_safe_token":
        "watch/executor/replay-safe-token-validate.py",
    "rollback_binding":
        "watch/rollback/rollback-binding-registry-validate.py",
}

VERIFIED_STATES = (
    "situation_state",
    "drift_state",
    "risk_state",
    "reasoning_state",
)

FUTURE_GATES = (
    "backup_binding",
    "rollback_binding",
    "approval_when_policy_requires",
    "execution_lease",
    "lease_ttl",
    "execution_window",
    "replay_safe_token",
    "execution_quorum",
    "validation",
    "execution_receipt",
    "receipt_chain",
    "execution_journal",
)


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_bool(value: Any) -> bool | None:
    if value is True or value is False:
        return value

    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized == "true":
            return True
        if normalized == "false":
            return False

    return None


def parse_timestamp(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)

    if not isinstance(value, str) or not value.strip():
        return None

    raw = value.strip()

    if raw.isdigit():
        return float(raw)

    try:
        return datetime.fromisoformat(
            raw.replace("Z", "+00:00")
        ).timestamp()
    except ValueError:
        return None


def age_seconds(value: Any) -> int | None:
    parsed = parse_timestamp(value)

    if parsed is None:
        return None

    return int(time.time() - parsed)


def load_key_value_status(path: Path) -> dict[str, str]:
    fields: dict[str, str] = {}

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()

        if not line or line.startswith("===") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()

        if key:
            fields[key] = value

    return fields


def load_json_object(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))

    if not isinstance(data, dict):
        raise ValueError("JSON root must be an object")

    return data


def proposal_identity(status: dict[str, str]) -> str:
    material = {
        "timestamp": status.get("timestamp", ""),
        "top_recommendation": status.get("top_recommendation", ""),
        "decision": status.get("decision", ""),
        "risk_class": status.get("risk_class", ""),
    }

    digest = hashlib.sha256(
        json.dumps(
            material,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()[:16]

    timestamp = "".join(
        character
        for character in status.get("timestamp", "")
        if character.isalnum()
    )

    timestamp = timestamp[:15] or "UNKNOWN"
    return f"THINK-{timestamp}-{digest}"


def validate_thinking(
    status: dict[str, str],
    max_age_seconds: int,
) -> list[str]:
    errors: list[str] = []

    required = (
        "timestamp",
        "top_recommendation",
        "decision",
        "risk_class",
        "overall",
        "advisory_only",
        "execution_allowed",
        "mutation_authority",
        *VERIFIED_STATES,
    )

    for key in required:
        if not status.get(key):
            errors.append(f"thinking_missing:{key}")

    if parse_bool(status.get("advisory_only")) is not True:
        errors.append("thinking_advisory_only_must_be_true")

    if parse_bool(status.get("execution_allowed")) is not False:
        errors.append("thinking_execution_allowed_must_be_false")

    if parse_bool(status.get("mutation_authority")) is not False:
        errors.append("thinking_mutation_authority_must_be_false")

    if status.get("overall") != "HEALTHY":
        errors.append("thinking_overall_must_be_HEALTHY")

    for key in VERIFIED_STATES:
        if status.get(key) != "VERIFIED":
            errors.append(f"thinking_{key}_must_be_VERIFIED")

    current_age = age_seconds(status.get("timestamp"))

    if current_age is None:
        errors.append("thinking_timestamp_invalid")
    elif current_age < -300:
        errors.append("thinking_timestamp_in_future")
    elif current_age > max_age_seconds:
        errors.append("thinking_status_stale")

    return errors


def validate_review(
    review: dict[str, Any] | None,
    proposal_id: str,
    recommendation: str,
    max_age_seconds: int,
) -> tuple[list[str], str]:
    if review is None:
        return ["review_journal_missing"], "MISSING"

    errors: list[str] = []

    required = (
        "ts",
        "request_id",
        "provider",
        "reviewer",
        "model",
        "review_type",
        "verdict",
        "execution_allowed",
        "result_blocked",
        "authority",
        "confidence",
        "review_bundle_sha256",
        "raw_response_sha256",
        "journal_path",
    )

    for key in required:
        if key not in review:
            errors.append(f"review_missing:{key}")

    verdict = str(review.get("verdict", "MISSING"))

    if verdict not in {"PASS", "FIX", "NO"}:
        errors.append("review_verdict_invalid")
    elif verdict != "PASS":
        errors.append(f"review_verdict_{verdict}")

    if review.get("request_id") != proposal_id:
        errors.append("review_request_id_mismatch")

    if review.get("provider") != "local":
        errors.append("review_provider_must_be_local")

    if review.get("reviewer") != "spot-worker-05":
        errors.append("reviewer_must_be_spot-worker-05")

    if review.get("review_type") != "policy_review":
        errors.append("review_type_must_be_policy_review")

    if review.get("authority") != "proposal_review_only":
        errors.append("review_authority_must_be_proposal_review_only")

    if review.get("execution_allowed") is not False:
        errors.append("review_execution_allowed_must_be_false")

    if review.get("result_blocked") is not True:
        errors.append("review_result_blocked_must_be_true")

    for key in ("review_bundle_sha256", "raw_response_sha256"):
        value = review.get(key)

        if not isinstance(value, str) or len(value) != 64:
            errors.append(f"review_{key}_invalid")

    review_age = age_seconds(review.get("ts"))

    if review_age is None:
        errors.append("review_timestamp_invalid")
    elif review_age < -300:
        errors.append("review_timestamp_in_future")
    elif review_age > max_age_seconds:
        errors.append("review_journal_stale")

    bundle = review.get("review_bundle")

    if not isinstance(bundle, dict):
        errors.append("review_bundle_missing")
    else:
        if bundle.get("request_id") != proposal_id:
            errors.append("review_bundle_request_id_mismatch")

        if bundle.get("review_type") != "policy_review":
            errors.append("review_bundle_type_mismatch")

        prompt = bundle.get("prompt")

        if not isinstance(prompt, str) or recommendation not in prompt:
            errors.append("review_bundle_recommendation_mismatch")

        policy = bundle.get("policy")

        if not isinstance(policy, dict):
            errors.append("review_bundle_policy_missing")
        else:
            expected_policy = {
                "execution_authority": "proposal_review_only",
                "spot_core_only_executor": True,
                "no_backup_no_change": True,
                "no_review_no_apply": True,
                "no_rollback_no_execution": True,
            }

            for key, expected in expected_policy.items():
                if policy.get(key) != expected:
                    errors.append(f"review_policy_mismatch:{key}")

    return errors, verdict


def run_contract_validators() -> tuple[dict[str, Any], list[str]]:
    results: dict[str, Any] = {}
    errors: list[str] = []

    for name, relative_path in CONTRACT_VALIDATORS.items():
        path = ROOT / relative_path

        if not path.is_file():
            results[name] = {
                "status": "FAIL",
                "source": relative_path,
                "reason": "validator_missing",
            }
            errors.append(f"contract_{name}_validator_missing")
            continue

        process = subprocess.run(
            [sys.executable, str(path)],
            cwd=ROOT,
            text=True,
            capture_output=True,
            timeout=120,
            check=False,
        )

        output_lines = [
            line.strip()
            for line in (process.stdout + "\n" + process.stderr).splitlines()
            if line.strip()
        ]

        results[name] = {
            "status": "PASS" if process.returncode == 0 else "FAIL",
            "source": relative_path,
            "return_code": process.returncode,
            "summary": output_lines[-1] if output_lines else "",
        }

        if process.returncode != 0:
            errors.append(f"contract_{name}_validation_failed")

    return results, errors


def build_result(
    thinking_status: Path,
    review_journal: Path | None,
    max_age_seconds: int,
) -> dict[str, Any]:
    status = load_key_value_status(thinking_status)
    proposal_id = proposal_identity(status)
    recommendation = status.get("top_recommendation", "")

    thinking_errors = validate_thinking(status, max_age_seconds)

    review: dict[str, Any] | None = None
    review_load_error = ""

    if review_journal is not None:
        try:
            review = load_json_object(review_journal)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            review_load_error = f"review_journal_unreadable:{type(exc).__name__}"

    review_errors, verdict = validate_review(
        review,
        proposal_id,
        recommendation,
        max_age_seconds,
    )

    if review_load_error:
        review_errors.append(review_load_error)

    contract_results, contract_errors = run_contract_validators()

    blockers = sorted(
        set(
            thinking_errors
            + review_errors
            + contract_errors
        )
    )

    eligible = not blockers

    return {
        "schema_version": "1.0",
        "module": "module47_governed_recommendation_review_gate",
        "generated_at": utc_now(),
        "mode": "read_only",
        "advisory_only": True,
        "decision": (
            "ELIGIBLE_FOR_NEXT_GATE"
            if eligible
            else "BLOCKED"
        ),
        "eligible_for_next_gate": eligible,
        "next_gate": "BACKUP_AND_ROLLBACK_BINDING",
        "proposal": {
            "proposal_id": proposal_id,
            "timestamp": status.get("timestamp"),
            "top_recommendation": recommendation,
            "decision": status.get("decision"),
            "risk_class": status.get("risk_class"),
            "overall": status.get("overall"),
            "errors": thinking_errors,
        },
        "review": {
            "journal_present": review is not None,
            "journal_path": (
                str(review_journal)
                if review_journal is not None
                else None
            ),
            "request_id": (
                review.get("request_id")
                if review is not None
                else None
            ),
            "reviewer": (
                review.get("reviewer")
                if review is not None
                else None
            ),
            "verdict": verdict,
            "authority": (
                review.get("authority")
                if review is not None
                else None
            ),
            "errors": review_errors,
        },
        "future_contracts": contract_results,
        "required_future_gates": list(FUTURE_GATES),
        "blockers": blockers,
        "safety": {
            "spot_core_sole_executor": True,
            "worker_self_apply": False,
            "approval_authority": False,
            "execution_allowed": False,
            "mutation_authority": False,
            "mutation_performed": False,
            "executor_dispatch_performed": False,
            "backup_created": False,
            "rollback_executed": False,
            "review_requested": False,
            "journal_written": False,
            "step6_authorized": False,
            "eligibility_does_not_authorize_execution": True,
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluate a verified Thinking recommendation and immutable review journal."
    )
    parser.add_argument("--thinking-status", required=True)
    parser.add_argument("--review-journal")
    parser.add_argument("--max-age-seconds", type=int, default=900)
    parser.add_argument("--proposal-id-only", action="store_true")
    parser.add_argument("--recommendation-only", action="store_true")
    parser.add_argument("--require-eligible", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    thinking_path = Path(args.thinking_status)

    if not thinking_path.is_file():
        raise SystemExit("[FAIL] thinking status file does not exist")

    status = load_key_value_status(thinking_path)

    if args.proposal_id_only:
        print(proposal_identity(status))
        return 0

    if args.recommendation_only:
        print(status.get("top_recommendation", ""))
        return 0

    review_path = (
        Path(args.review_journal)
        if args.review_journal
        else None
    )

    result = build_result(
        thinking_path,
        review_path,
        args.max_age_seconds,
    )

    print(json.dumps(result, indent=2, sort_keys=True))

    if args.require_eligible and not result["eligible_for_next_gate"]:
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
