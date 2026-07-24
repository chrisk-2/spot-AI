#!/usr/bin/env python3
"""Validate the immutable Module 47 gate runner and status surface."""

from __future__ import annotations

import json
import stat
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUNNER = ROOT / "watch/review/recommendation-review-gate.py"
EVALUATOR = ROOT / "watch/review/recommendation-review-eligibility.py"


def run(arguments: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(RUNNER), *arguments],
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=300,
        check=False,
    )


def evaluator(arguments: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(EVALUATOR), *arguments],
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=180,
        check=False,
    )


def write_status(path: Path) -> None:
    timestamp = datetime.now(
        timezone.utc
    ).strftime("%Y-%m-%dT%H:%M:%SZ")

    path.write_text(
        "\n".join(
            (
                f"timestamp={timestamp}",
                "top_recommendation=continue-observation-cadence",
                "advisory_only=true",
                "execution_allowed=false",
                "mutation_authority=false",
                "decision=CONTINUE_OBSERVATION",
                "concern_count=0",
                "risk_class=LOW",
                "overall=HEALTHY",
                "situation_state=VERIFIED",
                "drift_state=VERIFIED",
                "risk_state=VERIFIED",
                "reasoning_state=VERIFIED",
                "",
            )
        ),
        encoding="utf-8",
    )


def proposal_id(status_path: Path) -> str:
    process = evaluator(
        [
            "--thinking-status",
            str(status_path),
            "--proposal-id-only",
        ]
    )

    if process.returncode != 0:
        raise RuntimeError(process.stderr or process.stdout)

    return process.stdout.strip()


def review_record(identity: str) -> dict:
    recommendation = "continue-observation-cadence"

    return {
        "ts": int(time.time()),
        "ts_utc": datetime.now(
            timezone.utc
        ).strftime("%Y%m%dT%H%M%SZ"),
        "request_id": identity,
        "provider": "local",
        "reviewer": "spot-worker-05",
        "model": "qwen2.5-coder:32b",
        "review_type": "policy_review",
        "verdict": "PASS",
        "execution_allowed": False,
        "result_blocked": True,
        "authority": "proposal_review_only",
        "confidence": "high",
        "review_bundle_sha256": "a" * 64,
        "raw_response_sha256": "b" * 64,
        "journal_path": "/tmp/module47-review.json",
        "review_bundle": {
            "request_id": identity,
            "review_type": "policy_review",
            "prompt": (
                "Review this verified recommendation: "
                f"{recommendation}"
            ),
            "policy": {
                "execution_authority": "proposal_review_only",
                "spot_core_only_executor": True,
                "no_backup_no_change": True,
                "no_review_no_apply": True,
                "no_rollback_no_execution": True,
            },
        },
    }


def assert_safety(result: dict) -> None:
    safety = result["safety"]

    assert safety["spot_core_sole_executor"] is True
    assert safety["worker_self_apply"] is False
    assert safety["review_requested"] is False
    assert safety["review_journal_written"] is False
    assert safety["gate_decision_journal_only"] is True
    assert safety["backup_created"] is False
    assert safety["rollback_executed"] is False
    assert safety["approval_authority"] is False
    assert safety["execution_allowed"] is False
    assert safety["mutation_authority"] is False
    assert safety["mutation_performed"] is False
    assert safety["executor_dispatch_performed"] is False
    assert safety["step6_authorized"] is False


def main() -> int:
    passed = 0

    with tempfile.TemporaryDirectory(
        prefix="spot-module47-gate-validator-"
    ) as temporary_directory:
        root = Path(temporary_directory)
        status_path = root / "thinking-status.txt"
        history_path = root / "review-history.jsonl"
        journal_root = root / "gate-journal"

        write_status(status_path)
        identity = proposal_id(status_path)

        history_path.write_text(
            json.dumps(review_record(identity)) + "\n",
            encoding="utf-8",
        )

        process = run(
            [
                "run",
                "--thinking-status",
                str(status_path),
                "--review-history",
                str(history_path),
                "--journal-root",
                str(journal_root),
                "--require-eligible",
            ]
        )

        if process.returncode != 0:
            print(process.stdout)
            print(process.stderr, file=sys.stderr)
            raise SystemExit("[FAIL] valid correlated gate run failed")

        result = json.loads(process.stdout)
        assert_safety(result)

        assert result["record_written"] is True
        assert result["correlated_review_found"] is True
        assert (
            result["eligibility"]["decision"]
            == "ELIGIBLE_FOR_NEXT_GATE"
        )
        assert (
            result["eligibility"]["eligible_for_next_gate"]
            is True
        )

        record_path = Path(result["record_path"])
        assert record_path.is_file()
        assert stat.S_IMODE(record_path.stat().st_mode) == 0o444

        persisted = json.loads(
            record_path.read_text(encoding="utf-8")
        )
        assert persisted == result

        passed += 1
        print("[PASS] eligible decision written as immutable gate record")

        process = run(
            [
                "status",
                "--journal-root",
                str(journal_root),
            ]
        )

        assert process.returncode == 0

        status = json.loads(process.stdout)

        assert status["action"] == "GATE_STATUS"
        assert status["mode"] == "read_only"
        assert status["status"] == "PRESENT"
        assert status["status_read_only"] is True
        assert status["record_mode"] == "0444"
        assert status["record_path"] == str(record_path)
        assert status["record"] == result
        assert status["safety"]["execution_allowed"] is False
        assert status["safety"]["mutation_authority"] is False
        assert status["safety"]["step6_authorized"] is False

        passed += 1
        print("[PASS] status command reads latest record without mutation")

        missing_history = root / "missing-review-history.jsonl"
        blocked_root = root / "blocked-journal"

        process = run(
            [
                "run",
                "--thinking-status",
                str(status_path),
                "--review-history",
                str(missing_history),
                "--journal-root",
                str(blocked_root),
                "--no-write",
            ]
        )

        assert process.returncode == 0

        blocked = json.loads(process.stdout)
        assert_safety(blocked)

        assert blocked["record_written"] is False
        assert blocked["record_path"] is None
        assert blocked["correlated_review_found"] is False
        assert blocked["eligibility"]["decision"] == "BLOCKED"
        assert (
            "review_journal_missing"
            in blocked["eligibility"]["blockers"]
        )
        assert not blocked_root.exists()

        passed += 1
        print("[PASS] missing review fails closed without journal write")

    print(f"pass={passed} fail=0")
    print("RESULT: PASS")
    print("execution_allowed=false")
    print("mutation_authority=false")
    print("step6_authorized=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
