#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from thinking_common import (
    THINKING_ROOT,
    read_json,
    record_id,
    utc_now,
    write_record,
)

MEMORY_ROOT = Path("/mnt/collective/memory/spot")


def nested(
    value: dict[str, Any],
    *keys: str,
) -> Any:
    current: Any = value

    for key in keys:
        if not isinstance(current, dict):
            return None

        current = current.get(key)

    return current


def verified_latest_thought(
    category: str,
    schema: str,
) -> dict[str, Any] | None:
    index = THINKING_ROOT / category / "index.jsonl"

    if not index.is_file():
        return None

    try:
        lines = [
            line.strip()
            for line in index.read_text(
                encoding="utf-8"
            ).splitlines()
            if line.strip()
        ]
    except OSError:
        return None

    for line in reversed(lines):
        try:
            entry = json.loads(line)
            artifact = Path(entry["artifact"])
            expected = str(entry["sha256"])

            if not artifact.is_file():
                continue

            actual = hashlib.sha256(
                artifact.read_bytes()
            ).hexdigest()

            if actual != expected:
                continue

            value = read_json(artifact)

            if not isinstance(value, dict):
                continue

            if value.get("schema") != schema:
                continue

            return value
        except (
            OSError,
            KeyError,
            TypeError,
            json.JSONDecodeError,
        ):
            continue

    return None


def verified_memory_reference(
    category: str,
) -> dict[str, Any] | None:
    index = MEMORY_ROOT / category / "index.jsonl"

    if not index.is_file():
        return None

    try:
        lines = [
            line.strip()
            for line in index.read_text(
                encoding="utf-8"
            ).splitlines()
            if line.strip()
        ]
    except OSError:
        return None

    for line in reversed(lines):
        try:
            entry = json.loads(line)
            artifact = Path(entry["artifact"])
            checksum = Path(entry["checksum"])

            if not artifact.is_file():
                continue

            if not checksum.is_file():
                continue

            checksum_line = checksum.read_text(
                encoding="utf-8"
            ).strip()

            expected = checksum_line.split()[0]
            actual = hashlib.sha256(
                artifact.read_bytes()
            ).hexdigest()

            if actual != expected:
                continue

            return {
                "record_id": entry.get("record_id"),
                "artifact": str(artifact),
                "checksum": str(checksum),
                "sha256": actual,
                "verified": True,
            }
        except (
            OSError,
            KeyError,
            TypeError,
            IndexError,
            json.JSONDecodeError,
        ):
            continue

    return None


def recommendation(
    recommendation_id: str,
    priority: str,
    category: str,
    action: str,
    rationale: str,
    evidence: list[str],
    operator_review_required: bool = False,
) -> dict[str, Any]:
    return {
        "recommendation_id": recommendation_id,
        "priority": priority,
        "category": category,
        "action": action,
        "rationale": rationale,
        "evidence": evidence,
        "mode": "advisory_only",
        "operator_review_required":
            operator_review_required,
        "approval_granted": False,
        "execution_requested": False,
        "execution_allowed": False,
        "mutation_authority": False,
    }


def main() -> None:
    situation = verified_latest_thought(
        "situation",
        "spot.thinking.situation.v1",
    )
    drift = verified_latest_thought(
        "drift",
        "spot.thinking.drift.v1",
    )
    risk = verified_latest_thought(
        "risk",
        "spot.thinking.risk.v1",
    )

    operator_memory = verified_memory_reference(
        "operator"
    )
    strategy_memory = verified_memory_reference(
        "strategy"
    )

    missing_evidence: list[str] = []

    if situation is None:
        missing_evidence.append("situation")

    if drift is None:
        missing_evidence.append("drift")

    if risk is None:
        missing_evidence.append("risk")

    situation_state = str(
        nested(
            situation or {},
            "situation",
            "state",
        )
        or "UNKNOWN"
    )
    drift_state = str(
        nested(
            drift or {},
            "drift",
            "state",
        )
        or "UNKNOWN"
    )
    drift_direction = str(
        nested(
            drift or {},
            "drift",
            "direction",
        )
        or "UNKNOWN"
    )
    risk_class = str(
        nested(
            risk or {},
            "risk",
            "classification",
        )
        or "UNKNOWN"
    )
    risk_score = nested(
        risk or {},
        "risk",
        "score",
    )
    recommended_posture = str(
        nested(
            risk or {},
            "risk",
            "recommended_posture",
        )
        or "evidence_required"
    )

    recommendations: list[dict[str, Any]] = []

    if missing_evidence:
        decision = "REFRESH_EVIDENCE"
        reasoning_state = "INCOMPLETE"

        recommendations.append(
            recommendation(
                "refresh-thinking-evidence",
                "P1",
                "evidence",
                (
                    "Run the missing read-only Thinking "
                    "Loop assessments"
                ),
                (
                    "Operational reasoning requires a "
                    "verified situation, drift, and risk chain"
                ),
                missing_evidence,
            )
        )
    elif risk_class in {"CRITICAL", "HIGH"}:
        decision = "OPERATOR_INTERVENTION"
        reasoning_state = "ACTION-HELD"

        recommendations.append(
            recommendation(
                "hold-nonessential-change",
                "P1",
                "safety",
                (
                    "Hold nonessential operational changes "
                    "and escalate the observed condition"
                ),
                (
                    f"Risk is {risk_class} with score "
                    f"{risk_score}"
                ),
                [
                    f"risk_class={risk_class}",
                    f"risk_score={risk_score}",
                    f"situation_state={situation_state}",
                    f"drift_direction={drift_direction}",
                ],
                operator_review_required=True,
            )
        )
    elif risk_class == "ELEVATED":
        decision = "INVESTIGATE"
        reasoning_state = "REVIEW-REQUIRED"

        recommendations.append(
            recommendation(
                "investigate-elevated-risk",
                "P1",
                "investigation",
                (
                    "Investigate the elevated-risk evidence "
                    "before advancing operational work"
                ),
                (
                    "Elevated risk permits analysis and "
                    "proposal preparation, not execution"
                ),
                [
                    f"risk_score={risk_score}",
                    f"situation_state={situation_state}",
                    f"drift_direction={drift_direction}",
                ],
                operator_review_required=True,
            )
        )
    elif risk_class == "GUARDED":
        decision = "REVIEW"
        reasoning_state = "ADVISORY"

        recommendations.append(
            recommendation(
                "review-guarded-condition",
                "P2",
                "review",
                (
                    "Review the guarded condition while "
                    "preserving read-only operation"
                ),
                (
                    "The evidence does not require a halt, "
                    "but it is not fully nominal"
                ),
                [
                    f"risk_score={risk_score}",
                    f"situation_state={situation_state}",
                    f"drift_state={drift_state}",
                ],
            )
        )
    else:
        decision = "CONTINUE_OBSERVATION"
        reasoning_state = "NOMINAL"

        if drift_state == "BASELINE":
            recommendations.append(
                recommendation(
                    "collect-second-situation-sample",
                    "P2",
                    "observation",
                    (
                        "Collect the next situation sample "
                        "before drawing a drift trend"
                    ),
                    (
                        "The first drift record establishes "
                        "a baseline but cannot show a trend"
                    ),
                    [
                        "drift_state=BASELINE",
                        f"risk_score={risk_score}",
                        f"situation_state={situation_state}",
                    ],
                )
            )
        elif drift_state == "STABLE":
            recommendations.append(
                recommendation(
                    "continue-observation-cadence",
                    "P3",
                    "observation",
                    (
                        "Continue the current read-only "
                        "observation cadence"
                    ),
                    (
                        "The verified situation is nominal "
                        "and no material drift was detected"
                    ),
                    [
                        "drift_state=STABLE",
                        f"risk_score={risk_score}",
                        f"situation_state={situation_state}",
                    ],
                )
            )
        elif drift_direction == "IMPROVING":
            recommendations.append(
                recommendation(
                    "confirm-improving-trend",
                    "P3",
                    "observation",
                    (
                        "Confirm the improving condition with "
                        "another read-only assessment"
                    ),
                    (
                        "One improving comparison is useful "
                        "but does not establish a durable trend"
                    ),
                    [
                        "drift_direction=IMPROVING",
                        f"risk_score={risk_score}",
                    ],
                )
            )
        else:
            recommendations.append(
                recommendation(
                    "continue-read-only-analysis",
                    "P3",
                    "observation",
                    (
                        "Continue read-only analysis and "
                        "preserve the current governance posture"
                    ),
                    (
                        "Current risk does not justify an "
                        "operational hold"
                    ),
                    [
                        f"drift_state={drift_state}",
                        f"drift_direction={drift_direction}",
                        f"risk_score={risk_score}",
                    ],
                )
            )

    if operator_memory is None:
        recommendations.append(
            recommendation(
                "refresh-operator-memory",
                "P3",
                "continuity",
                (
                    "Refresh the append-only operator memory "
                    "snapshot"
                ),
                (
                    "No verified operator-memory reference "
                    "was available to the reasoning cycle"
                ),
                ["operator_memory_verified=false"],
            )
        )

    if strategy_memory is None:
        recommendations.append(
            recommendation(
                "refresh-strategy-memory",
                "P3",
                "continuity",
                (
                    "Refresh the append-only strategy memory "
                    "snapshot"
                ),
                (
                    "No verified strategy-memory reference "
                    "was available to the reasoning cycle"
                ),
                ["strategy_memory_verified=false"],
            )
        )

    recommendations.sort(
        key=lambda item: (
            item["priority"],
            item["recommendation_id"],
        )
    )

    top_recommendation = (
        recommendations[0]["recommendation_id"]
        if recommendations
        else None
    )

    summary = (
        f"Situation {situation_state}; "
        f"drift {drift_state}/{drift_direction}; "
        f"risk {risk_class}"
        f" ({risk_score}); "
        f"decision {decision}; "
        f"posture {recommended_posture}. "
        "Execution remains blocked."
    )

    record = {
        "schema": "spot.thinking.reasoning.v1",
        "record_id": record_id("reasoning"),
        "timestamp": utc_now(),
        "module": 45,
        "thinking_stage": "operational_reasoning",
        "mode":
            "read_only_governed_advisory_reasoning",
        "identity": {
            "behavior":
                "governance_first_operational_intelligence",
            "validation_before_mutation": True,
            "rollback_first_thinking": True,
            "audit_preservation": True,
            "concise_operational_communication": True,
        },
        "authority": {
            "reasoning_authority": True,
            "proposal_authority": True,
            "approval_authority": False,
            "execution_allowed": False,
            "mutation_authority": False,
            "spot_core_sole_executor": True,
        },
        "sources": {
            "situation_id": (
                situation.get("record_id")
                if situation
                else None
            ),
            "drift_id": (
                drift.get("record_id")
                if drift
                else None
            ),
            "risk_id": (
                risk.get("record_id")
                if risk
                else None
            ),
            "operator_memory": operator_memory,
            "strategy_memory": strategy_memory,
            "missing_evidence": missing_evidence,
        },
        "reasoning": {
            "state": reasoning_state,
            "decision": decision,
            "summary": summary,
            "situation_state": situation_state,
            "drift_state": drift_state,
            "drift_direction": drift_direction,
            "risk_class": risk_class,
            "risk_score": risk_score,
            "recommended_posture":
                recommended_posture,
            "top_recommendation":
                top_recommendation,
            "recommendation_count":
                len(recommendations),
            "recommendations": recommendations,
        },
        "governance": {
            "read_only": True,
            "advisory_only": True,
            "proposal_only": True,
            "self_approval": False,
            "auto_apply": False,
            "worker_self_apply": False,
            "execution_allowed": False,
            "mutation_authority": False,
        },
    }

    paths = write_record(
        "reasoning",
        record,
    )

    print(f"artifact={paths['artifact']}")
    print(f"checksum={paths['checksum']}")
    print(f"index={paths['index']}")
    print(f"reasoning_state={reasoning_state}")
    print(f"decision={decision}")
    print(f"risk_class={risk_class}")
    print(f"risk_score={risk_score}")
    print(
        "top_recommendation="
        f"{top_recommendation}"
    )
    print(
        "recommendation_count="
        f"{len(recommendations)}"
    )
    print("approval_authority=false")
    print("execution_allowed=false")
    print("mutation_authority=false")


if __name__ == "__main__":
    main()
