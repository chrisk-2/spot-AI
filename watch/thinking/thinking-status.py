#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

from thinking_common import (
    THINKING_ROOT,
    read_json,
    utc_now,
)

CATEGORIES = {
    "situation": "spot.thinking.situation.v1",
    "drift": "spot.thinking.drift.v1",
    "risk": "spot.thinking.risk.v1",
    "reasoning": "spot.thinking.reasoning.v1",
}


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
) -> dict[str, Any]:
    index = THINKING_ROOT / category / "index.jsonl"

    if not index.is_file():
        return {
            "state": "NOT-PRESENT",
            "record": None,
            "artifact": None,
            "checksum_valid": False,
        }

    try:
        lines = [
            line.strip()
            for line in index.read_text(
                encoding="utf-8"
            ).splitlines()
            if line.strip()
        ]
    except OSError:
        return {
            "state": "INDEX-UNREADABLE",
            "record": None,
            "artifact": None,
            "checksum_valid": False,
        }

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

            record = read_json(artifact)

            if not isinstance(record, dict):
                continue

            if record.get("schema") != schema:
                continue

            return {
                "state": "VERIFIED",
                "record": record,
                "artifact": str(artifact),
                "checksum_valid": True,
                "sha256": actual,
            }
        except (
            OSError,
            KeyError,
            TypeError,
            json.JSONDecodeError,
        ):
            continue

    return {
        "state": "NO-VERIFIED-RECORD",
        "record": None,
        "artifact": None,
        "checksum_valid": False,
    }


def main() -> None:
    raw = {
        category: verified_latest(
            category,
            schema,
        )
        for category, schema in CATEGORIES.items()
    }

    verified_count = sum(
        1
        for value in raw.values()
        if value["state"] == "VERIFIED"
    )

    if verified_count == len(CATEGORIES):
        overall = "HEALTHY"
    elif verified_count:
        overall = "PARTIAL"
    else:
        overall = "EMPTY"

    situation = raw["situation"]["record"] or {}
    drift = raw["drift"]["record"] or {}
    risk = raw["risk"]["record"] or {}
    reasoning = raw["reasoning"]["record"] or {}

    status = {
        "schema": "spot.thinking.status.v1",
        "timestamp": utc_now(),
        "mode": "read_only",
        "thinking_root": str(THINKING_ROOT),
        "overall": overall,
        "verified_categories": verified_count,
        "expected_categories": len(CATEGORIES),
        "categories": {
            category: {
                "state": value["state"],
                "record_id": (
                    value["record"].get("record_id")
                    if value["record"]
                    else None
                ),
                "timestamp": (
                    value["record"].get("timestamp")
                    if value["record"]
                    else None
                ),
                "artifact": value["artifact"],
                "checksum_valid":
                    value["checksum_valid"],
            }
            for category, value in raw.items()
        },
        "current": {
            "situation_state": nested(
                situation,
                "situation",
                "state",
            ),
            "situation_confidence": nested(
                situation,
                "situation",
                "confidence",
            ),
            "concern_count": nested(
                situation,
                "situation",
                "concern_count",
            ),
            "drift_state": nested(
                drift,
                "drift",
                "state",
            ),
            "drift_direction": nested(
                drift,
                "drift",
                "direction",
            ),
            "drift_event_count": nested(
                drift,
                "drift",
                "event_count",
            ),
            "risk_score": nested(
                risk,
                "risk",
                "score",
            ),
            "risk_class": nested(
                risk,
                "risk",
                "classification",
            ),
            "recommended_posture": nested(
                risk,
                "risk",
                "recommended_posture",
            ),
            "reasoning_state": nested(
                reasoning,
                "reasoning",
                "state",
            ),
            "decision": nested(
                reasoning,
                "reasoning",
                "decision",
            ),
            "top_recommendation": nested(
                reasoning,
                "reasoning",
                "top_recommendation",
            ),
            "recommendation_count": nested(
                reasoning,
                "reasoning",
                "recommendation_count",
            ),
        },
        "governance": {
            "read_only": True,
            "append_only_thinking_memory": True,
            "advisory_only": True,
            "proposal_only": True,
            "self_approval": False,
            "auto_apply": False,
            "worker_self_apply": False,
            "approval_authority": False,
            "execution_allowed": False,
            "mutation_authority": False,
            "spot_core_sole_executor": True,
        },
    }

    if "--json" in sys.argv[1:]:
        print(
            json.dumps(
                status,
                indent=2,
                sort_keys=True,
            )
        )
        return

    current = status["current"]

    print("===== SPOT THINKING STATUS =====")
    print(f"timestamp={status['timestamp']}")
    print(f"overall={status['overall']}")
    print(
        "verified_categories="
        f"{verified_count}/{len(CATEGORIES)}"
    )

    for category in CATEGORIES:
        value = status["categories"][category]

        print(
            f"{category}_state={value['state']}"
        )
        print(
            f"{category}_record_id="
            f"{value['record_id']}"
        )
        print(
            f"{category}_checksum_valid="
            f"{str(value['checksum_valid']).lower()}"
        )

    print(
        "situation_state="
        f"{current['situation_state']}"
    )
    print(
        "situation_confidence="
        f"{current['situation_confidence']}"
    )
    print(
        "concern_count="
        f"{current['concern_count']}"
    )
    print(
        "drift_state="
        f"{current['drift_state']}"
    )
    print(
        "drift_direction="
        f"{current['drift_direction']}"
    )
    print(
        "risk_score="
        f"{current['risk_score']}"
    )
    print(
        "risk_class="
        f"{current['risk_class']}"
    )
    print(
        "reasoning_state="
        f"{current['reasoning_state']}"
    )
    print(
        "decision="
        f"{current['decision']}"
    )
    print(
        "top_recommendation="
        f"{current['top_recommendation']}"
    )
    print("advisory_only=true")
    print("approval_authority=false")
    print("execution_allowed=false")
    print("mutation_authority=false")


if __name__ == "__main__":
    main()
