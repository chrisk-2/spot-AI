#!/usr/bin/env python3
"""Validate Module 47 governed recommendation eligibility behavior."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EVALUATOR = ROOT / "watch/review/recommendation-review-eligibility.py"


def run(arguments: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(EVALUATOR), *arguments],
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=180,
        check=False,
    )


def write_status(path: Path, timestamp: str) -> None:
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
    process = run(
        [
            "--thinking-status",
            str(status_path),
            "--proposal-id-only",
        ]
    )

    if process.returncode != 0:
        raise RuntimeError(process.stderr or process.stdout)

    return process.stdout.strip()


def review_record(
    request_id: str,
    recommendation: str,
    verdict: str = "PASS",
) -> dict:
    return {
        "ts": int(time.time()),
        "ts_utc": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
        "request_id": request_id,
        "provider": "local",
        "reviewer": "spot-worker-05",
        "model": "qwen2.5-coder:32b",
        "review_type": "policy_review",
        "verdict": verdict,
        "execution_allowed": False,
        "result_blocked": True,
        "authority": "proposal_review_only",
        "confidence": "high",
        "review_bundle_sha256": "a" * 64,
        "raw_response_sha256": "b" * 64,
        "journal_path": "/tmp/module47-review.json",
        "review_bundle": {
            "request_id": request_id,
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


def assert_invariants(result: dict) -> None:
    safety = result["safety"]

    assert result["mode"] == "read_only"
    assert result["advisory_only"] is True
    assert safety["spot_core_sole_executor"] is True
    assert safety["worker_self_apply"] is False
    assert safety["approval_authority"] is False
    assert safety["execution_allowed"] is False
    assert safety["mutation_authority"] is False
    assert safety["mutation_performed"] is False
    assert safety["executor_dispatch_performed"] is False
    assert safety["review_requested"] is False
    assert safety["journal_written"] is False
    assert safety["step6_authorized"] is False


def main() -> int:
    passed = 0

    with tempfile.TemporaryDirectory(
        prefix="spot-module47-validator-"
    ) as temporary_directory:
        root = Path(temporary_directory)
        status_path = root / "thinking-status.txt"
        review_path = root / "review.json"

        current_timestamp = datetime.now(
            timezone.utc
        ).strftime("%Y-%m-%dT%H:%M:%SZ")

        write_status(status_path, current_timestamp)

        identity = proposal_id(status_path)

        review_path.write_text(
            json.dumps(
                review_record(
                    identity,
                    "continue-observation-cadence",
                )
            ),
            encoding="utf-8",
        )

        process = run(
            [
                "--thinking-status",
                str(status_path),
                "--review-journal",
                str(review_path),
                "--require-eligible",
            ]
        )

        if process.returncode != 0:
            print(process.stdout)
            print(process.stderr, file=sys.stderr)
            raise SystemExit("[FAIL] valid fixture was not eligible")

        result = json.loads(process.stdout)
        assert_invariants(result)

        assert result["decision"] == "ELIGIBLE_FOR_NEXT_GATE"
        assert result["eligible_for_next_gate"] is True
        assert result["blockers"] == []
        passed += 1
        print("[PASS] valid correlated PASS review is eligible for next gate")

        no_review = review_record(
            identity,
            "continue-observation-cadence",
            verdict="NO",
        )
        review_path.write_text(
            json.dumps(no_review),
            encoding="utf-8",
        )

        process = run(
            [
                "--thinking-status",
                str(status_path),
                "--review-journal",
                str(review_path),
                "--require-eligible",
            ]
        )

        assert process.returncode != 0
        result = json.loads(process.stdout)
        assert_invariants(result)
        assert result["decision"] == "BLOCKED"
        assert "review_verdict_NO" in result["blockers"]
        passed += 1
        print("[PASS] NO verdict fails closed")

        mismatched = review_record(
            "THINK-MISMATCH",
            "continue-observation-cadence",
        )
        review_path.write_text(
            json.dumps(mismatched),
            encoding="utf-8",
        )

        process = run(
            [
                "--thinking-status",
                str(status_path),
                "--review-journal",
                str(review_path),
                "--require-eligible",
            ]
        )

        assert process.returncode != 0
        result = json.loads(process.stdout)
        assert_invariants(result)
        assert result["decision"] == "BLOCKED"
        assert "review_request_id_mismatch" in result["blockers"]
        passed += 1
        print("[PASS] mismatched recommendation identity fails closed")

        stale_timestamp = datetime.fromtimestamp(
            time.time() - 3600,
            timezone.utc,
        ).strftime("%Y-%m-%dT%H:%M:%SZ")

        write_status(status_path, stale_timestamp)
        stale_identity = proposal_id(status_path)

        review_path.write_text(
            json.dumps(
                review_record(
                    stale_identity,
                    "continue-observation-cadence",
                )
            ),
            encoding="utf-8",
        )

        process = run(
            [
                "--thinking-status",
                str(status_path),
                "--review-journal",
                str(review_path),
                "--max-age-seconds",
                "900",
                "--require-eligible",
            ]
        )

        assert process.returncode != 0
        result = json.loads(process.stdout)
        assert_invariants(result)
        assert result["decision"] == "BLOCKED"
        assert "thinking_status_stale" in result["blockers"]
        passed += 1
        print("[PASS] stale Thinking recommendation fails closed")

        write_status(status_path, current_timestamp)

        process = run(
            [
                "--thinking-status",
                str(status_path),
            ]
        )

        assert process.returncode == 0
        result = json.loads(process.stdout)
        assert_invariants(result)
        assert result["decision"] == "BLOCKED"
        assert "review_journal_missing" in result["blockers"]
        passed += 1
        print("[PASS] missing review journal fails closed")

    print(f"pass={passed} fail=0")
    print("RESULT: PASS")
    print("execution_allowed=false")
    print("mutation_authority=false")
    print("step6_authorized=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
