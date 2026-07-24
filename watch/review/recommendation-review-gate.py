#!/usr/bin/env python3
"""Run and journal the Module 47 governed recommendation review gate.

The runner captures the current Thinking status, selects only a correlated
immutable local-review record, invokes the fail-closed eligibility evaluator,
and optionally appends one immutable gate-decision record.

It never requests a review, creates a backup, grants authority, dispatches an
executor, or authorizes mutation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
OPERATOR = ROOT / "watch/operator/spot-operator.sh"
EVALUATOR = ROOT / "watch/review/recommendation-review-eligibility.py"

DEFAULT_REVIEW_HISTORY = Path(
    "/mnt/collective/logs/spot/reviews/local-review-history.jsonl"
)
DEFAULT_JOURNAL_ROOT = Path(
    "/mnt/collective/logs/spot/reviews/recommendation-review-gate"
)


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def run_process(arguments: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        arguments,
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=300,
        check=False,
    )


def capture_thinking_status(path: Path) -> None:
    process = run_process(
        [
            "bash",
            str(OPERATOR),
            "thinking-status",
        ]
    )

    if process.returncode != 0:
        raise RuntimeError(
            process.stderr.strip()
            or process.stdout.strip()
            or "thinking-status failed"
        )

    path.write_text(process.stdout, encoding="utf-8")


def proposal_id(status_path: Path) -> str:
    process = run_process(
        [
            sys.executable,
            str(EVALUATOR),
            "--thinking-status",
            str(status_path),
            "--proposal-id-only",
        ]
    )

    if process.returncode != 0:
        raise RuntimeError(
            process.stderr.strip()
            or process.stdout.strip()
            or "proposal identity failed"
        )

    identity = process.stdout.strip()

    if not identity.startswith("THINK-"):
        raise RuntimeError("invalid proposal identity")

    return identity


def read_review_history(
    path: Path,
    expected_request_id: str,
) -> dict[str, Any] | None:
    if not path.is_file():
        return None

    selected: dict[str, Any] | None = None

    for raw_line in path.read_text(
        encoding="utf-8",
        errors="replace",
    ).splitlines():
        line = raw_line.strip()

        if not line:
            continue

        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue

        if not isinstance(record, dict):
            continue

        if record.get("request_id") == expected_request_id:
            selected = record

    return selected


def evaluate(
    status_path: Path,
    review_record: dict[str, Any] | None,
    max_age_seconds: int,
    temporary_root: Path,
) -> dict[str, Any]:
    arguments = [
        sys.executable,
        str(EVALUATOR),
        "--thinking-status",
        str(status_path),
        "--max-age-seconds",
        str(max_age_seconds),
    ]

    if review_record is not None:
        review_path = temporary_root / "correlated-review.json"
        review_path.write_text(
            json.dumps(review_record, sort_keys=True),
            encoding="utf-8",
        )
        arguments.extend(["--review-journal", str(review_path)])

    process = run_process(arguments)

    if process.returncode != 0:
        raise RuntimeError(
            process.stderr.strip()
            or process.stdout.strip()
            or "eligibility evaluation failed"
        )

    result = json.loads(process.stdout)

    if not isinstance(result, dict):
        raise RuntimeError("eligibility evaluator returned a non-object")

    safety = result.get("safety")

    if not isinstance(safety, dict):
        raise RuntimeError("eligibility result has no safety object")

    required_safety = {
        "spot_core_sole_executor": True,
        "worker_self_apply": False,
        "approval_authority": False,
        "execution_allowed": False,
        "mutation_authority": False,
        "mutation_performed": False,
        "executor_dispatch_performed": False,
        "review_requested": False,
        "journal_written": False,
        "step6_authorized": False,
        "eligibility_does_not_authorize_execution": True,
    }

    for key, expected in required_safety.items():
        if safety.get(key) is not expected:
            raise RuntimeError(f"unsafe eligibility result: {key}")

    return result


def safe_name(value: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9_.-]", "_", value)
    return normalized[:96] or "UNKNOWN"


def encode_record(record: dict[str, Any]) -> bytes:
    return (
        json.dumps(
            record,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def write_immutable_record(
    journal_root: Path,
    record: dict[str, Any],
) -> Path:
    journal_root.mkdir(parents=True, exist_ok=True)

    generated_at = str(record["generated_at"])
    timestamp_name = re.sub(r"[^0-9TZ]", "", generated_at)
    proposal_name = safe_name(str(record["proposal_id"]))

    digest_material = json.dumps(
        record,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")

    digest = hashlib.sha256(digest_material).hexdigest()[:16]

    record_path = journal_root / (
        f"{timestamp_name}-{proposal_name}-{digest}.json"
    )

    record["record_path"] = str(record_path)
    record["record_written"] = True

    payload = encode_record(record)

    try:
        descriptor = os.open(
            record_path,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL,
            0o444,
        )
    except FileExistsError:
        existing = record_path.read_bytes()

        if existing != payload:
            raise RuntimeError(
                "immutable gate record collision with different content"
            )

        return record_path

    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    except BaseException:
        try:
            record_path.unlink()
        except OSError:
            pass
        raise

    record_path.chmod(0o444)
    return record_path


def run_gate(args: argparse.Namespace) -> int:
    review_history = Path(args.review_history)
    journal_root = Path(args.journal_root)

    with tempfile.TemporaryDirectory(
        prefix="spot-module47-gate-"
    ) as temporary_directory:
        temporary_root = Path(temporary_directory)

        if args.thinking_status:
            status_path = Path(args.thinking_status)

            if not status_path.is_file():
                raise RuntimeError("supplied Thinking status does not exist")
        else:
            status_path = temporary_root / "thinking-status.txt"
            capture_thinking_status(status_path)

        identity = proposal_id(status_path)
        review_record = read_review_history(
            review_history,
            identity,
        )

        eligibility = evaluate(
            status_path,
            review_record,
            args.max_age_seconds,
            temporary_root,
        )

    record: dict[str, Any] = {
        "schema_version": "1.0",
        "module": "module47_governed_recommendation_review_gate",
        "action": "GATE_EVALUATION",
        "mode": "read_only",
        "generated_at": utc_now(),
        "proposal_id": identity,
        "review_history_path": str(review_history),
        "correlated_review_found": review_record is not None,
        "record_written": False,
        "record_path": None,
        "eligibility": eligibility,
        "safety": {
            "spot_core_sole_executor": True,
            "worker_self_apply": False,
            "review_requested": False,
            "review_journal_written": False,
            "gate_decision_journal_only": True,
            "backup_created": False,
            "rollback_executed": False,
            "approval_authority": False,
            "execution_allowed": False,
            "mutation_authority": False,
            "mutation_performed": False,
            "executor_dispatch_performed": False,
            "step6_authorized": False,
        },
    }

    if not args.no_write:
        write_immutable_record(journal_root, record)

    print(json.dumps(record, indent=2, sort_keys=True))

    if (
        args.require_eligible
        and not eligibility.get("eligible_for_next_gate", False)
    ):
        return 1

    return 0


def latest_record(journal_root: Path) -> Path | None:
    if not journal_root.is_dir():
        return None

    candidates = sorted(
        path
        for path in journal_root.glob("*.json")
        if path.is_file()
    )

    if not candidates:
        return None

    return candidates[-1]


def show_status(args: argparse.Namespace) -> int:
    journal_root = Path(args.journal_root)
    record_path = latest_record(journal_root)

    if record_path is None:
        result = {
            "schema_version": "1.0",
            "module": "module47_governed_recommendation_review_gate",
            "action": "GATE_STATUS",
            "mode": "read_only",
            "status": "MISSING",
            "status_read_only": True,
            "record_path": None,
            "record": None,
            "safety": {
                "execution_allowed": False,
                "mutation_authority": False,
                "mutation_performed": False,
                "step6_authorized": False,
            },
        }
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0

    record = json.loads(record_path.read_text(encoding="utf-8"))

    if not isinstance(record, dict):
        raise RuntimeError("latest gate record is not a JSON object")

    mode = stat.S_IMODE(record_path.stat().st_mode)

    result = {
        "schema_version": "1.0",
        "module": "module47_governed_recommendation_review_gate",
        "action": "GATE_STATUS",
        "mode": "read_only",
        "status": "PRESENT",
        "status_read_only": True,
        "record_path": str(record_path),
        "record_mode": f"{mode:04o}",
        "record": record,
        "safety": {
            "execution_allowed": False,
            "mutation_authority": False,
            "mutation_performed": False,
            "step6_authorized": False,
        },
    }

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run or inspect the governed recommendation review gate."
    )
    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("--thinking-status")
    run_parser.add_argument(
        "--review-history",
        default=str(DEFAULT_REVIEW_HISTORY),
    )
    run_parser.add_argument(
        "--journal-root",
        default=str(DEFAULT_JOURNAL_ROOT),
    )
    run_parser.add_argument(
        "--max-age-seconds",
        type=int,
        default=900,
    )
    run_parser.add_argument("--no-write", action="store_true")
    run_parser.add_argument("--require-eligible", action="store_true")

    status_parser = subparsers.add_parser("status")
    status_parser.add_argument(
        "--journal-root",
        default=str(DEFAULT_JOURNAL_ROOT),
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    try:
        if args.command == "run":
            return run_gate(args)

        if args.command == "status":
            return show_status(args)

        raise RuntimeError("unsupported command")
    except (
        OSError,
        ValueError,
        json.JSONDecodeError,
        RuntimeError,
        subprocess.TimeoutExpired,
    ) as exc:
        print(
            json.dumps(
                {
                    "module":
                        "module47_governed_recommendation_review_gate",
                    "decision": "BLOCKED",
                    "error": f"{type(exc).__name__}: {exc}",
                    "safety": {
                        "execution_allowed": False,
                        "mutation_authority": False,
                        "mutation_performed": False,
                        "executor_dispatch_performed": False,
                        "step6_authorized": False,
                    },
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
