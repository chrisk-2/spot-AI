#!/usr/bin/env python3
"""Adversarial validation for the dormant controlled read/observe runner."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

BASE = Path(__file__).resolve().parent
RUNNER = BASE / "controlled-read-observe.py"
EVIDENCE_VALIDATOR = BASE / "controlled-read-observe-evidence-validate.py"


def request(
    observation_id: str,
    request_id: str,
    target: str = "spot-remediation-fixture.service",
) -> dict[str, Any]:
    return {
        "schema": "spot_controlled_read_observe_request_v1",
        "observation_id": observation_id,
        "request_id": request_id,
        "requested_at": "2026-08-26T13:50:00Z",
        "hostname": "spot-core",
        "observer_identity": "spot-post239-k21b-validator",
        "observation_class": "systemd",
        "target": target,
        "operation": "systemd_show",
        "timeout_seconds": 5,
        "output_bytes_max": 4096,
        "execution_allowed": False,
        "mutation_authority": False,
        "live_executor_enabled": False,
    }


def write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def invoke(
    request_path: Path,
    evidence_dir: Path | None = None,
    fixture: bool = False,
) -> subprocess.CompletedProcess[str]:
    command = [
        sys.executable,
        str(RUNNER),
        "--request",
        str(request_path),
    ]

    if evidence_dir is not None:
        command.extend(["--evidence-dir", str(evidence_dir)])

    if fixture:
        command.append("--offline-validation-fixture")

    return subprocess.run(
        command,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=30,
    )


def validate_evidence_file(path: Path) -> None:
    completed = subprocess.run(
        [
            sys.executable,
            str(EVIDENCE_VALIDATOR),
            str(path),
        ],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=30,
    )
    assert completed.returncode == 0, completed.stderr


def main() -> int:
    assert RUNNER.is_file()
    assert EVIDENCE_VALIDATOR.is_file()

    source = RUNNER.read_text(encoding="utf-8")

    forbidden = (
        "subprocess",
        "os.system",
        "shell=True",
        "systemctl",
        "journalctl",
        "urllib",
        "requests",
        "paramiko",
        "ssh ",
    )

    for token in forbidden:
        assert token not in source, token

    print("[PASS] production execution surfaces absent")

    with tempfile.TemporaryDirectory(
        prefix="spot-post239-k21b-"
    ) as temporary:
        root = Path(temporary)
        requests = root / "requests"
        evidence = root / "evidence"
        requests.mkdir()

        valid_path = requests / "valid.json"
        valid = request(
            "OBS-K21B-VALID0001",
            "K21B-REQUEST-VALID0001",
        )
        write_json(valid_path, valid)

        denied = invoke(valid_path)

        assert denied.returncode == 3
        denied_record = json.loads(denied.stdout)
        assert denied_record["policy_decision"] == "denied_fail_closed"
        assert denied_record["classification"] == "unknown"
        assert denied_record["execution_allowed"] is False
        assert denied_record["mutation_authority"] is False
        assert denied_record["service_action_performed"] is False

        print("[PASS] default production path denied fail-closed")

        observed = invoke(
            valid_path,
            evidence_dir=evidence,
            fixture=True,
        )

        assert observed.returncode == 0, observed.stderr
        observed_record = json.loads(observed.stdout)
        assert observed_record["policy_decision"] == "allowed_read_only"
        assert observed_record["classification"] == "healthy"
        assert observed_record["exit_status"] == 0
        assert observed_record["output_bytes"] > 0
        assert observed_record["execution_allowed"] is False
        assert observed_record["mutation_authority"] is False
        assert observed_record["remediation_performed"] is False
        assert observed_record["service_action_performed"] is False
        assert observed_record["network_stack_mutation"] is False

        evidence_path = evidence / "OBS-K21B-VALID0001.json"
        assert evidence_path.is_file()
        validate_evidence_file(evidence_path)

        print("[PASS] offline fixture produced schema-valid evidence")

        collision = invoke(
            valid_path,
            evidence_dir=evidence,
            fixture=True,
        )

        assert collision.returncode == 2
        assert "identity collision" in collision.stderr

        print("[PASS] changed replay evidence rejected")

        invalid_path = requests / "invalid-target.json"
        invalid = request(
            "OBS-K21B-INVALID01",
            "K21B-REQUEST-INVALID01",
            target="glpi-agent.service",
        )
        write_json(invalid_path, invalid)

        rejected = invoke(
            invalid_path,
            evidence_dir=evidence,
            fixture=True,
        )

        assert rejected.returncode == 2
        assert "not allowlisted" in rejected.stderr
        assert not (evidence / "OBS-K21B-INVALID01.json").exists()

        print("[PASS] non-allowlisted service rejected without evidence write")

    print("pass=4 fail=0")
    print("observer_installed=false")
    print("observer_enabled=false")
    print("observer_scheduled=false")
    print("production_observation_performed=false")
    print("service_action_performed=false")
    print("execution_allowed=false")
    print("mutation_authority=false")
    print("RESULT: POST-2.39 K21B VALIDATION PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
