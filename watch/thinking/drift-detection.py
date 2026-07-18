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


def verified_situation_records(
    limit: int = 2,
) -> list[dict[str, Any]]:
    index = (
        THINKING_ROOT
        / "situation"
        / "index.jsonl"
    )

    if not index.is_file():
        return []

    try:
        lines = [
            line.strip()
            for line in index.read_text(
                encoding="utf-8"
            ).splitlines()
            if line.strip()
        ]
    except OSError:
        return []

    records: list[dict[str, Any]] = []

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

            if (
                record.get("schema")
                != "spot.thinking.situation.v1"
            ):
                continue

            records.append(record)

            if len(records) >= limit:
                break
        except (
            OSError,
            KeyError,
            TypeError,
            json.JSONDecodeError,
        ):
            continue

    return records


def change_event(
    field: str,
    before: Any,
    after: Any,
    severity: str,
    direction: str,
) -> dict[str, Any] | None:
    if before == after:
        return None

    return {
        "field": field,
        "before": before,
        "after": after,
        "severity": severity,
        "direction": direction,
    }


def compare_state(
    previous: str,
    current: str,
) -> tuple[str, str]:
    ranks = {
        "NOMINAL": 0,
        "ATTENTION": 1,
        "CRITICAL": 2,
    }

    before = ranks.get(previous)
    after = ranks.get(current)

    if before is None or after is None:
        return "MEDIUM", "CHANGED"

    if after > before:
        return "HIGH", "WORSENING"

    if after < before:
        return "INFO", "IMPROVING"

    return "INFO", "UNCHANGED"


def compare_boolean_health(
    before: Any,
    after: Any,
) -> tuple[str, str]:
    if before is True and after is False:
        return "CRITICAL", "WORSENING"

    if before is False and after is True:
        return "INFO", "IMPROVING"

    return "MEDIUM", "CHANGED"


def compare_numeric_health(
    before: Any,
    after: Any,
) -> tuple[str, str]:
    if (
        isinstance(before, int)
        and isinstance(after, int)
    ):
        if after < before:
            return "HIGH", "WORSENING"

        if after > before:
            return "INFO", "IMPROVING"

    return "MEDIUM", "CHANGED"


def main() -> None:
    situations = verified_situation_records(
        limit=2
    )

    current = (
        situations[0]
        if situations
        else None
    )
    previous = (
        situations[1]
        if len(situations) > 1
        else None
    )

    events: list[dict[str, Any]] = []

    if current is None:
        drift_state = "NO-EVIDENCE"
        direction = "UNKNOWN"
        baseline_established = False
        current_id = None
        previous_id = None
    elif previous is None:
        drift_state = "BASELINE"
        direction = "BASELINE"
        baseline_established = True
        current_id = current.get("record_id")
        previous_id = None
    else:
        baseline_established = True
        current_id = current.get("record_id")
        previous_id = previous.get("record_id")

        previous_state = str(
            nested(
                previous,
                "situation",
                "state",
            )
            or "UNKNOWN"
        )
        current_state = str(
            nested(
                current,
                "situation",
                "state",
            )
            or "UNKNOWN"
        )

        severity, event_direction = compare_state(
            previous_state,
            current_state,
        )

        event = change_event(
            "situation.state",
            previous_state,
            current_state,
            severity,
            event_direction,
        )

        if event:
            events.append(event)

        comparisons = [
            (
                "observations.core_api_ok",
                nested(
                    previous,
                    "observations",
                    "core_api_ok",
                ),
                nested(
                    current,
                    "observations",
                    "core_api_ok",
                ),
                compare_boolean_health,
            ),
            (
                "observations.workers_healthy",
                nested(
                    previous,
                    "observations",
                    "workers_healthy",
                ),
                nested(
                    current,
                    "observations",
                    "workers_healthy",
                ),
                compare_numeric_health,
            ),
            (
                "observations.workers_total",
                nested(
                    previous,
                    "observations",
                    "workers_total",
                ),
                nested(
                    current,
                    "observations",
                    "workers_total",
                ),
                compare_numeric_health,
            ),
        ]

        for (
            field,
            before,
            after,
            classifier,
        ) in comparisons:
            severity, event_direction = classifier(
                before,
                after,
            )

            event = change_event(
                field,
                before,
                after,
                severity,
                event_direction,
            )

            if event:
                events.append(event)

        text_comparisons = [
            (
                "observations.fleet_state",
                nested(
                    previous,
                    "observations",
                    "fleet_state",
                ),
                nested(
                    current,
                    "observations",
                    "fleet_state",
                ),
            ),
            (
                "observations.memory_state",
                nested(
                    previous,
                    "observations",
                    "memory_state",
                ),
                nested(
                    current,
                    "observations",
                    "memory_state",
                ),
            ),
        ]

        healthy_states = {
            "COMPLETE",
            "HEALTHY",
            "NOMINAL",
        }

        for field, before, after in text_comparisons:
            if before == after:
                continue

            if (
                before in healthy_states
                and after not in healthy_states
            ):
                severity = "HIGH"
                event_direction = "WORSENING"
            elif (
                before not in healthy_states
                and after in healthy_states
            ):
                severity = "INFO"
                event_direction = "IMPROVING"
            else:
                severity = "MEDIUM"
                event_direction = "CHANGED"

            events.append(
                {
                    "field": field,
                    "before": before,
                    "after": after,
                    "severity": severity,
                    "direction": event_direction,
                }
            )

        previous_concerns = set(
            nested(
                previous,
                "situation",
                "concerns",
            )
            or []
        )
        current_concerns = set(
            nested(
                current,
                "situation",
                "concerns",
            )
            or []
        )

        for concern in sorted(
            current_concerns - previous_concerns
        ):
            events.append(
                {
                    "field":
                        "situation.concerns",
                    "before": None,
                    "after": concern,
                    "severity": "MEDIUM",
                    "direction": "WORSENING",
                }
            )

        for concern in sorted(
            previous_concerns - current_concerns
        ):
            events.append(
                {
                    "field":
                        "situation.concerns",
                    "before": concern,
                    "after": None,
                    "severity": "INFO",
                    "direction": "IMPROVING",
                }
            )

        if events:
            drift_state = "CHANGED"
        else:
            drift_state = "STABLE"

        directions = {
            str(event["direction"])
            for event in events
        }

        worsening = "WORSENING" in directions
        improving = "IMPROVING" in directions

        if worsening and improving:
            direction = "MIXED"
        elif worsening:
            direction = "WORSENING"
        elif improving:
            direction = "IMPROVING"
        elif events:
            direction = "CHANGED"
        else:
            direction = "NONE"

    material_events = [
        event
        for event in events
        if event.get("severity")
        in {
            "MEDIUM",
            "HIGH",
            "CRITICAL",
        }
    ]

    record = {
        "schema": "spot.thinking.drift.v1",
        "record_id": record_id("drift"),
        "timestamp": utc_now(),
        "module": 43,
        "thinking_stage": "drift_detection",
        "mode": "read_only_deterministic_comparison",
        "authority": {
            "assessment_authority": True,
            "proposal_authority": False,
            "approval_authority": False,
            "execution_allowed": False,
            "mutation_authority": False,
            "spot_core_sole_executor": True,
        },
        "comparison": {
            "current_situation_id":
                current_id,
            "previous_situation_id":
                previous_id,
            "baseline_established":
                baseline_established,
        },
        "drift": {
            "state": drift_state,
            "direction": direction,
            "event_count": len(events),
            "material_event_count":
                len(material_events),
            "events": events,
        },
        "governance": {
            "read_only": True,
            "proposal_only": False,
            "auto_apply": False,
            "routing_mutation": False,
            "ownership_mutation": False,
            "execution_allowed": False,
            "mutation_authority": False,
        },
    }

    paths = write_record(
        "drift",
        record,
    )

    print(f"artifact={paths['artifact']}")
    print(f"checksum={paths['checksum']}")
    print(f"index={paths['index']}")
    print(f"drift_state={drift_state}")
    print(f"direction={direction}")
    print(f"event_count={len(events)}")
    print(
        "material_event_count="
        f"{len(material_events)}"
    )
    print("execution_allowed=false")
    print("mutation_authority=false")


if __name__ == "__main__":
    main()
