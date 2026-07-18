#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from thinking_common import (
    ROOT,
    record_id,
    read_json,
    run,
    sha256_text,
    utc_now,
    write_record,
)

OPERATOR = ROOT / "watch/operator/spot-operator.sh"
LIFE_STATE = ROOT / "watch/state/spot-life.json"


def http_json(url: str) -> dict[str, Any] | None:
    try:
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent":
                    "spot-situation-assessment/read-only"
            },
        )

        with urllib.request.urlopen(
            request,
            timeout=5,
        ) as response:
            if not 200 <= int(response.status) < 300:
                return None

            value = json.loads(
                response.read().decode("utf-8")
            )

            return value if isinstance(value, dict) else None
    except Exception:
        return None


def last_overall(output: str) -> str:
    matches = re.findall(
        r"(?im)^overall\s*[:=]\s*([A-Z0-9_-]+)",
        output,
    )

    return matches[-1].upper() if matches else "UNKNOWN"


def fresh_life_state() -> dict[str, Any] | None:
    value = read_json(LIFE_STATE)

    if not isinstance(value, dict):
        return None

    timestamp = value.get("timestamp")

    if not isinstance(timestamp, str):
        return None

    try:
        observed = datetime.fromisoformat(
            timestamp.replace("Z", "+00:00")
        )
        age_seconds = (
            datetime.now(timezone.utc) - observed
        ).total_seconds()
    except ValueError:
        return None

    if age_seconds < 0 or age_seconds > 1800:
        return None

    return value


def unique(values: list[str]) -> list[str]:
    output: list[str] = []

    for value in values:
        if value and value not in output:
            output.append(value)

    return output


def main() -> None:
    fleet_command = run(
        [str(OPERATOR), "fleet-health"],
        timeout=900,
    )
    memory_command = run(
        [str(OPERATOR), "memory-status"],
        timeout=180,
    )

    core_health = http_json(
        "http://127.0.0.1:8787/health"
    )
    fleet_ping = http_json(
        "http://127.0.0.1:8787/fleet/ping"
    )

    fleet_state = last_overall(
        fleet_command["stdout"]
    )
    memory_state = last_overall(
        memory_command["stdout"]
    )

    worker_records: dict[str, Any] = {}

    if isinstance(fleet_ping, dict):
        raw_workers = fleet_ping.get(
            "workers",
            fleet_ping,
        )

        if isinstance(raw_workers, dict):
            worker_records = {
                name: value
                for name, value in raw_workers.items()
                if name.startswith("spot-worker-")
                and isinstance(value, dict)
            }

    workers_total = len(worker_records)
    workers_healthy = 0
    unhealthy_workers: list[str] = []

    for name, value in sorted(worker_records.items()):
        healthy = (
            value.get("ok") is True
            and value.get("eligible") is not False
            and value.get("quarantined") is not True
        )

        if healthy:
            workers_healthy += 1
        else:
            unhealthy_workers.append(name)

    life = fresh_life_state()
    life_concerns: list[str] = []

    if isinstance(life, dict):
        raw_concerns = life.get("open_concerns", [])

        if isinstance(raw_concerns, list):
            life_concerns = [
                str(item)
                for item in raw_concerns
                if str(item).strip()
            ]

    core_ok = bool(
        isinstance(core_health, dict)
        and core_health.get("ok") is True
    )

    concerns: list[str] = []

    if not core_ok:
        concerns.append("Spot Core health endpoint unavailable")

    if fleet_command["returncode"] != 0:
        concerns.append(
            "fleet-health command did not complete cleanly"
        )

    if fleet_state not in {"COMPLETE", "HEALTHY"}:
        concerns.append(
            f"fleet health state is {fleet_state}"
        )

    if memory_command["returncode"] != 0:
        concerns.append(
            "memory-status command did not complete cleanly"
        )

    if memory_state != "HEALTHY":
        concerns.append(
            f"memory state is {memory_state}"
        )

    if workers_total == 0:
        concerns.append(
            "worker health records unavailable"
        )
    elif unhealthy_workers:
        concerns.extend(
            f"{name} is not healthy and eligible"
            for name in unhealthy_workers
        )

    concerns.extend(life_concerns)
    concerns = unique(concerns)

    critical = (
        not core_ok
        or bool(unhealthy_workers)
        or workers_total == 0
    )

    if critical:
        situation_state = "CRITICAL"
        recommended_focus = (
            "stabilize Spot Core or unhealthy workers "
            "before advancing the Thinking Loop"
        )
    elif concerns:
        situation_state = "ATTENTION"
        recommended_focus = (
            "review observed concerns and preserve "
            "read-only operation"
        )
    else:
        situation_state = "NOMINAL"
        recommended_focus = (
            "continue observation and proceed with "
            "read-only drift analysis"
        )

    evidence_count = sum(
        [
            core_health is not None,
            fleet_ping is not None,
            fleet_command["returncode"] == 0,
            memory_command["returncode"] == 0,
        ]
    )

    if evidence_count == 4:
        confidence = "HIGH"
    elif evidence_count >= 2:
        confidence = "MEDIUM"
    else:
        confidence = "LOW"

    record = {
        "schema": "spot.thinking.situation.v1",
        "record_id": record_id("situation"),
        "timestamp": utc_now(),
        "module": 42,
        "thinking_stage": "situation_assessment",
        "mode": "read_only_deterministic_assessment",
        "authority": {
            "assessment_authority": True,
            "proposal_authority": False,
            "approval_authority": False,
            "execution_allowed": False,
            "mutation_authority": False,
            "spot_core_sole_executor": True,
        },
        "situation": {
            "state": situation_state,
            "confidence": confidence,
            "concern_count": len(concerns),
            "concerns": concerns,
            "recommended_focus": recommended_focus,
        },
        "observations": {
            "core_api_ok": core_ok,
            "fleet_state": fleet_state,
            "memory_state": memory_state,
            "workers_total": workers_total,
            "workers_healthy": workers_healthy,
            "unhealthy_workers": unhealthy_workers,
            "fresh_life_state_used": life is not None,
        },
        "evidence": {
            "fleet_health": {
                "returncode":
                    fleet_command["returncode"],
                "timed_out":
                    fleet_command["timed_out"],
                "sha256":
                    sha256_text(
                        fleet_command["stdout"]
                        + fleet_command["stderr"]
                    ),
            },
            "memory_status": {
                "returncode":
                    memory_command["returncode"],
                "timed_out":
                    memory_command["timed_out"],
                "sha256":
                    sha256_text(
                        memory_command["stdout"]
                        + memory_command["stderr"]
                    ),
            },
            "core_health_present":
                core_health is not None,
            "fleet_ping_present":
                fleet_ping is not None,
        },
        "governance": {
            "read_only": True,
            "proposal_only": False,
            "auto_apply": False,
            "execution_allowed": False,
            "mutation_authority": False,
        },
    }

    paths = write_record("situation", record)

    print(f"artifact={paths['artifact']}")
    print(f"checksum={paths['checksum']}")
    print(f"index={paths['index']}")
    print(f"situation_state={situation_state}")
    print(f"confidence={confidence}")
    print(f"concern_count={len(concerns)}")
    print("execution_allowed=false")
    print("mutation_authority=false")


if __name__ == "__main__":
    main()
