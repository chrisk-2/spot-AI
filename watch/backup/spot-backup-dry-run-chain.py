#!/usr/bin/env python3
"""
Phase 2.33 dry-run backup chain aggregator.

Builds one reviewable dry-run transaction package from:
- manifest JSON
- validation report JSON
- journal event JSON

Writes package JSON to stdout only.

No live reads.
No live writes.
No journal append.
No backup writes.
No executor dispatch.
No service/config mutation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


PHASE = "2.33"
MODE = "dry_run_chain"


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_json(path: str) -> dict:
    return json.loads(Path(path).read_text())


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def build_chain(manifest_file: str, validation_file: str, journal_file: str) -> dict:
    manifest = load_json(manifest_file)
    validation = load_json(validation_file)
    journal = load_json(journal_file)

    request_id = manifest.get("request_id")

    return {
        "chain_version": "1.0",
        "chain_id": f"dryrun-chain-{uuid4()}",
        "timestamp_utc": utc_now(),
        "phase": PHASE,
        "mode": MODE,
        "request_id": request_id,
        "target": manifest.get("target"),
        "service": manifest.get("service"),
        "risk_class": manifest.get("risk_class"),
        "artifacts": {
            "manifest_file": manifest_file,
            "manifest_sha256": sha256_file(manifest_file),
            "validation_file": validation_file,
            "validation_sha256": sha256_file(validation_file),
            "journal_file": journal_file,
            "journal_sha256": sha256_file(journal_file),
        },
        "results": {
            "manifest_validation_result": manifest.get("validation_result"),
            "external_validation_result": validation.get("validation_result"),
            "journal_event_validation_result": journal.get("event_validation_result"),
        },
        "safety_assertions": {
            "execution_allowed": False,
            "fail_closed": True,
            "live_source_reads_performed": False,
            "live_backup_writes_performed": False,
            "journal_append_performed": False,
            "executor_dispatch_performed": False,
            "service_mutation_performed": False,
            "config_mutation_performed": False,
        },
        "review_requirements": {
            "worker05_grounded_review_required": True,
            "execution_allowed_after_review": False,
            "review_authority": "proposal_review_only",
        },
    }


def validate_chain(chain: dict) -> list[str]:
    errors: list[str] = []

    if chain.get("phase") != PHASE:
        errors.append("phase_must_be_2.33")

    if chain.get("mode") != MODE:
        errors.append("mode_must_be_dry_run_chain")

    results = chain.get("results", {})
    for key in [
        "manifest_validation_result",
        "external_validation_result",
        "journal_event_validation_result",
    ]:
        if results.get(key) != "PASS":
            errors.append(f"{key}_must_be_PASS")

    safety = chain.get("safety_assertions", {})
    expected_false = [
        "execution_allowed",
        "live_source_reads_performed",
        "live_backup_writes_performed",
        "journal_append_performed",
        "executor_dispatch_performed",
        "service_mutation_performed",
        "config_mutation_performed",
    ]
    for key in expected_false:
        if safety.get(key) is not False:
            errors.append(f"{key}_must_be_false")

    if safety.get("fail_closed") is not True:
        errors.append("fail_closed_must_be_true")

    review = chain.get("review_requirements", {})
    if review.get("worker05_grounded_review_required") is not True:
        errors.append("worker05_grounded_review_required_must_be_true")

    if review.get("execution_allowed_after_review") is not False:
        errors.append("execution_allowed_after_review_must_be_false")

    return errors


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Aggregate Phase 2.33 dry-run backup transaction chain."
    )
    parser.add_argument("--manifest-file", required=True)
    parser.add_argument("--validation-file", required=True)
    parser.add_argument("--journal-file", required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    chain = build_chain(args.manifest_file, args.validation_file, args.journal_file)
    errors = validate_chain(chain)

    chain["chain_validation_result"] = "PASS" if not errors else "FAIL"
    chain["chain_validation_errors"] = errors

    print(json.dumps(chain, indent=2, sort_keys=True))

    return 0 if not errors else 2


if __name__ == "__main__":
    raise SystemExit(main())
