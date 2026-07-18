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


def verified_latest(
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


def factor(
    factors: list[dict[str, Any]],
    factor_id: str,
    domain: str,
    points: int,
    evidence: Any,
    description: str,
) -> None:
    if points == 0:
        return

    factors.append(
        {
            "factor_id": factor_id,
            "domain": domain,
            "points": points,
            "evidence": evidence,
            "description": description,
        }
    )


def risk_class(score: int) -> str:
    if score >= 90:
        return "CRITICAL"

    if score >= 70:
        return "HIGH"

    if score >= 40:
        return "ELEVATED"

    if score >= 20:
        return "GUARDED"

    return "LOW"


def recommended_posture(
    classification: str,
) -> str:
    values = {
        "LOW":
            "observe_and_continue",
        "GUARDED":
            "observe_and_review",
        "ELEVATED":
            "hold_advancement_and_investigate",
        "HIGH":
            "halt_nonessential_changes",
        "CRITICAL":
            "operator_intervention_required",
    }

    return values[classification]


def main() -> None:
    situation = verified_latest(
        "situation",
        "spot.thinking.situation.v1",
    )
    drift = verified_latest(
        "drift",
        "spot.thinking.drift.v1",
    )

    factors: list[dict[str, Any]] = []

    if situation is None:
        factor(
            factors,
            "missing_situation_evidence",
            "evidence",
            50,
            None,
            "No verified situation assessment is available",
        )
        situation_state = "UNKNOWN"
        concerns: list[str] = []
        core_ok = None
        workers_total = None
        workers_healthy = None
        fleet_state = "UNKNOWN"
        memory_state = "UNKNOWN"
    else:
        situation_state = str(
            nested(
                situation,
                "situation",
                "state",
            )
            or "UNKNOWN"
        )

        raw_concerns = nested(
            situation,
            "situation",
            "concerns",
        )

        concerns = (
            [str(item) for item in raw_concerns]
            if isinstance(raw_concerns, list)
            else []
        )

        core_ok = nested(
            situation,
            "observations",
            "core_api_ok",
        )
        workers_total = nested(
            situation,
            "observations",
            "workers_total",
        )
        workers_healthy = nested(
            situation,
            "observations",
            "workers_healthy",
        )
        fleet_state = str(
            nested(
                situation,
                "observations",
                "fleet_state",
            )
            or "UNKNOWN"
        )
        memory_state = str(
            nested(
                situation,
                "observations",
                "memory_state",
            )
            or "UNKNOWN"
        )

    situation_points = {
        "NOMINAL": 0,
        "ATTENTION": 30,
        "CRITICAL": 60,
        "UNKNOWN": 20,
    }.get(situation_state, 20)

    factor(
        factors,
        "situation_classification",
        "overall",
        situation_points,
        situation_state,
        "Current deterministic situation classification",
    )

    if core_ok is False:
        factor(
            factors,
            "core_api_unavailable",
            "availability",
            40,
            core_ok,
            "Spot Core health endpoint is unavailable",
        )
    elif core_ok is None:
        factor(
            factors,
            "core_api_unknown",
            "evidence",
            15,
            core_ok,
            "Spot Core health could not be verified",
        )

    if (
        isinstance(workers_total, int)
        and isinstance(workers_healthy, int)
    ):
        missing_workers = max(
            workers_total - workers_healthy,
            0,
        )

        factor(
            factors,
            "worker_health_deficit",
            "availability",
            min(missing_workers * 15, 45),
            {
                "workers_total": workers_total,
                "workers_healthy": workers_healthy,
                "deficit": missing_workers,
            },
            "Workers are unavailable, ineligible, or quarantined",
        )
    else:
        factor(
            factors,
            "worker_health_unknown",
            "evidence",
            15,
            {
                "workers_total": workers_total,
                "workers_healthy": workers_healthy,
            },
            "Worker health totals are unavailable",
        )

    if fleet_state not in {"COMPLETE", "HEALTHY"}:
        factor(
            factors,
            "fleet_health_not_nominal",
            "availability",
            20,
            fleet_state,
            "Fleet health rollup is not healthy or complete",
        )

    if memory_state != "HEALTHY":
        factor(
            factors,
            "memory_health_not_nominal",
            "continuity",
            15,
            memory_state,
            "Persistent operational memory is not healthy",
        )

    concern_points = min(len(concerns) * 5, 20)

    factor(
        factors,
        "open_concerns",
        "operations",
        concern_points,
        concerns,
        "Open concerns require operator awareness",
    )

    if drift is None:
        drift_state = "UNKNOWN"
        drift_direction = "UNKNOWN"

        factor(
            factors,
            "missing_drift_evidence",
            "evidence",
            15,
            None,
            "No verified drift assessment is available",
        )
    else:
        drift_state = str(
            nested(
                drift,
                "drift",
                "state",
            )
            or "UNKNOWN"
        )
        drift_direction = str(
            nested(
                drift,
                "drift",
                "direction",
            )
            or "UNKNOWN"
        )

        direction_points = {
            "WORSENING": 25,
            "MIXED": 15,
            "CHANGED": 10,
            "UNKNOWN": 10,
            "BASELINE": 0,
            "NONE": 0,
            "IMPROVING": -10,
        }.get(drift_direction, 10)

        factor(
            factors,
            "drift_direction",
            "change",
            direction_points,
            drift_direction,
            "Direction of change between situation assessments",
        )

        events = nested(
            drift,
            "drift",
            "events",
        )

        if isinstance(events, list):
            event_points = 0

            for event in events:
                if not isinstance(event, dict):
                    continue

                event_points += {
                    "CRITICAL": 20,
                    "HIGH": 10,
                    "MEDIUM": 5,
                    "INFO": 0,
                }.get(
                    str(event.get("severity")),
                    0,
                )

            factor(
                factors,
                "material_drift_events",
                "change",
                min(event_points, 30),
                {
                    "event_count": len(events),
                    "calculated_points":
                        min(event_points, 30),
                },
                "Material drift events increase operational risk",
            )

    raw_score = sum(
        int(item["points"])
        for item in factors
    )
    score = max(0, min(raw_score, 100))
    classification = risk_class(score)
    posture = recommended_posture(classification)

    review_required = classification in {
        "ELEVATED",
        "HIGH",
        "CRITICAL",
    }

    record = {
        "schema": "spot.thinking.risk.v1",
        "record_id": record_id("risk"),
        "timestamp": utc_now(),
        "module": 44,
        "thinking_stage": "risk_assessment",
        "mode": "read_only_deterministic_scoring",
        "authority": {
            "assessment_authority": True,
            "proposal_authority": False,
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
        },
        "risk": {
            "score": score,
            "raw_score": raw_score,
            "classification": classification,
            "recommended_posture": posture,
            "operator_review_required":
                review_required,
            "factor_count": len(factors),
            "factors": factors,
        },
        "context": {
            "situation_state": situation_state,
            "drift_state": drift_state,
            "drift_direction": drift_direction,
            "core_api_ok": core_ok,
            "workers_total": workers_total,
            "workers_healthy": workers_healthy,
            "fleet_state": fleet_state,
            "memory_state": memory_state,
            "concern_count": len(concerns),
        },
        "governance": {
            "read_only": True,
            "advisory_only": True,
            "auto_apply": False,
            "self_approval": False,
            "execution_allowed": False,
            "mutation_authority": False,
        },
    }

    paths = write_record(
        "risk",
        record,
    )

    print(f"artifact={paths['artifact']}")
    print(f"checksum={paths['checksum']}")
    print(f"index={paths['index']}")
    print(f"risk_score={score}")
    print(f"risk_class={classification}")
    print(f"recommended_posture={posture}")
    print(
        "operator_review_required="
        f"{str(review_required).lower()}"
    )
    print("execution_allowed=false")
    print("mutation_authority=false")


if __name__ == "__main__":
    main()
