# Post-2.39 K21B Dormant Observer Implementation Review

## Review request

Worker-05 must review the K21B dormant runner implementation.
Review code and offline validation only.
Do not authorize installation, activation, scheduling, or production observation.

## Correlation

- repository head: `2835caa80d3fcd48354bb5a9558518aa2686dc8c`
- generated UTC: `2026-08-26T13:53:30Z`
- design review PASS: `watch/review/bundles/POST239-READ-OBSERVE-GATES-PASS-20260826T134350Z.json`
- operator authorization: `watch/review/bundles/AUTH-POST239-READ-OBSERVE-IMPLEMENTATION-20260826T134524Z.json`

## Required PASS conditions

- production execution surfaces are absent
- default runner path denies fail-closed
- only the built-in offline validation fixture can succeed
- requests must pass the committed schema and allowlist
- evidence must pass the committed schema
- non-allowlisted targets are rejected before evidence creation
- evidence writes use exclusive creation
- changed replay evidence fails closed
- implementation_present is true
- lane status remains inactive
- observer remains uninstalled, disabled, and unscheduled
- execution_allowed remains false
- mutation_authority remains false

## Offline validation results

- K21A deterministic/replay/bounds suite: PASS
- K21B dormant-runner adversarial suite: 4 PASS / 0 FAIL
- production observations performed: 0
- service actions performed: 0
- installations performed: 0

## Artifact hashes

```text
b7df48a2ba4277cbf496aee58d7376ba2d95fa7a45e0a16eced58bbcb2771b2f  watch/observe/controlled-read-observe.py
f46e88781c0bd4950d08fcf3fea9792e716460fe1bd8d85b371de81a5b011208  watch/observe/controlled-read-observe-validate.py
1315e4b0345d8d1b2925afa8ae8db99caba5256e1d0e7b7a3d4a7ff6bea4025c  watch/observe/controlled-read-observe-allowlist-v1.json
eb05366a2176ddcbd1f47a328f48fe620813981b979c5c0f14d690011f68cd0c  watch/observe/controlled-read-observe-replay-bounds-validate.py
23482e7cd0118909fa6d591515dcf3298ae1011a15637a42978a9a5fa3a4890c  watch/observe/controlled_read_observe_validation_v1.py
```

## Current machine-readable state

```json
{
  "status": "inactive",
  "implementation_present": true,
  "activation_authorized": false,
  "observer_installed": false,
  "observer_enabled": false,
  "observer_scheduled": false,
  "governance": {
    "execution_allowed": false,
    "live_executor_enabled": false,
    "mutation_authority": false,
    "network_mutation_allowed": false,
    "remediation_allowed": false,
    "remote_execution_allowed": false,
    "service_action_allowed": false
  }
}
```

## Dormant runner source

```python
#!/usr/bin/env python3
"""Dormant controlled read/observe runner.

Production observation remains blocked. The only permitted execution path is
the deterministic built-in offline fixture used by the K21B validator.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import socket
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from controlled_read_observe_validation_v1 import (
    ContractError,
    validate_evidence,
    validate_request,
)

SCHEMA = "spot_controlled_read_observe_evidence_v1"
OFFLINE_OUTPUT = b"controlled read observe offline validation fixture\n"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_request(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ContractError(f"cannot load request: {exc}") from exc

    if not isinstance(payload, dict):
        raise ContractError("request top-level JSON must be an object")

    validate_request(payload)
    return payload


def evidence_base(
    request: dict[str, Any],
    started_at: str,
    completed_at: str,
) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "observation_id": request["observation_id"],
        "request_id": request["request_id"],
        "timestamp": completed_at,
        "hostname": "spot-core",
        "observer_identity": request["observer_identity"],
        "observation_class": request["observation_class"],
        "target": request["target"],
        "operation": request["operation"],
        "started_at": started_at,
        "completed_at": completed_at,
        "timeout_seconds": request["timeout_seconds"],
        "exit_status": None,
        "http_status": None,
        "output_bytes": 0,
        "output_truncated": False,
        "output_sha256": hashlib.sha256(b"").hexdigest(),
        "classification": "unknown",
        "policy_decision": "denied_fail_closed",
        "execution_allowed": False,
        "mutation_authority": False,
        "live_executor_enabled": False,
        "remediation_performed": False,
        "service_action_performed": False,
        "network_stack_mutation": False,
    }


def deny_inactive(request: dict[str, Any]) -> dict[str, Any]:
    timestamp = utc_now()
    evidence = evidence_base(request, timestamp, timestamp)
    validate_evidence(evidence)
    return evidence


def run_offline_fixture(request: dict[str, Any]) -> dict[str, Any]:
    if socket.gethostname() != "spot-core":
        raise ContractError("offline fixture host identity mismatch")

    started_at = utc_now()
    output_limit = request["output_bytes_max"]
    captured = OFFLINE_OUTPUT[:output_limit]
    truncated = len(OFFLINE_OUTPUT) > output_limit
    completed_at = utc_now()

    evidence = evidence_base(request, started_at, completed_at)
    evidence.update(
        {
            "exit_status": 0,
            "output_bytes": len(captured),
            "output_truncated": truncated,
            "output_sha256": hashlib.sha256(captured).hexdigest(),
            "classification": "healthy",
            "policy_decision": "allowed_read_only",
        }
    )

    validate_evidence(evidence)
    return evidence


def encode(record: dict[str, Any]) -> bytes:
    return (
        json.dumps(record, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")


def write_replay_safe(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

    try:
        descriptor = os.open(
            path,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL,
            0o600,
        )
    except FileExistsError:
        if path.read_bytes() != payload:
            raise ContractError(
                "observation identity collision with different evidence"
            )
        return

    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    except BaseException:
        try:
            path.unlink()
        except OSError:
            pass
        raise


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Dormant controlled read/observe runner"
    )
    parser.add_argument("--request", required=True, type=Path)
    parser.add_argument("--evidence-dir", type=Path)
    parser.add_argument(
        "--offline-validation-fixture",
        action="store_true",
    )
    args = parser.parse_args()

    try:
        request = load_request(args.request)

        if args.offline_validation_fixture:
            evidence = run_offline_fixture(request)
        else:
            evidence = deny_inactive(request)

        payload = encode(evidence)

        if args.evidence_dir is not None:
            destination = (
                args.evidence_dir /
                f"{request['observation_id']}.json"
            )
            write_replay_safe(destination, payload)

        sys.stdout.buffer.write(payload)

        if evidence["policy_decision"] == "denied_fail_closed":
            return 3

        return 0

    except ContractError as exc:
        print(f"[DENY] controlled observation rejected: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
```

## Adversarial validator source

```python
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
```

## Required response

```json
{
  "verdict": "PASS|FIX|NO",
  "execution_allowed": false,
  "confidence": "high|medium|low",
  "intent_match": "pass|fail",
  "policy_match": "pass|fail",
  "phase_match": "pass|fail",
  "backup_required": false,
  "backup_verified": false,
  "rollback_defined": false,
  "validation_defined": true,
  "required_fixes": [],
  "blocking_findings": [],
  "notes": "REQUIRED"
}
```
