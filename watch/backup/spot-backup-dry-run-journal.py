#!/usr/bin/env python3
"""
Phase 2.32 dry-run backup journal event generator.

Reads:
- dry-run manifest JSON
- optional validation report JSON

Writes:
- journal event JSON to stdout only

Does not:
- append to live journals
- create backup artifacts
- read live source files
- dispatch executor
- mutate services/config
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


PHASE = "2.32"
MODE = "dry_run_journal"


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_json(path: str | None) -> dict:
    try:
        if path:
            return json.loads(Path(path).read_text())
        return json.loads(sys.stdin.read())
    except json.JSONDecodeError as exc:
        raise SystemExit(f"ERROR: invalid JSON: {exc}") from exc


def build_event(manifest: dict, validation: dict | None) -> dict:
    event_id = f"dryrun-journal-{uuid4()}"

    validation_result = None
    validation_errors = []

    if validation:
        validation_result = validation.get("validation_result")
        validation_errors = validation.get("errors", [])

    return {
        "event_version": "1.0",
        "event_id": event_id,
        "timestamp_utc": utc_now(),
        "phase": PHASE,
        "mode": MODE,
        "event_type": "backup_dry_run_manifest_journal",
        "request_id": manifest.get("request_id"),
        "target": manifest.get("target"),
        "service": manifest.get("service"),
        "risk_class": manifest.get("risk_class"),
        "manifest_phase": manifest.get("phase"),
        "manifest_mode": manifest.get("mode"),
        "manifest_validation_result": manifest.get("validation_result"),
        "external_validation_result": validation_result,
        "external_validation_errors": validation_errors,
        "proposed_backup_root": manifest.get("proposed_backup_root"),
        "proposed_backup_path": manifest.get("proposed_backup_path"),
        "requested_paths": manifest.get("requested_paths"),
        "execution_allowed": False,
        "fail_closed": True,
        "journal_write_performed": False,
        "live_source_reads_performed": False,
        "live_backup_writes_performed": False,
        "executor_dispatch_performed": False,
        "service_mutation_performed": False,
        "config_mutation_performed": False,
        "notes": [
            "stdout-only dry-run journal event",
            "no append to live journal",
            "no backup artifact writes",
            "no executor dispatch",
            "no mutation",
        ],
    }


def validate_event(event: dict) -> list[str]:
    errors: list[str] = []

    required = [
        "event_version",
        "event_id",
        "timestamp_utc",
        "phase",
        "mode",
        "event_type",
        "request_id",
        "target",
        "service",
        "risk_class",
        "execution_allowed",
        "fail_closed",
        "journal_write_performed",
        "live_source_reads_performed",
        "live_backup_writes_performed",
        "executor_dispatch_performed",
        "service_mutation_performed",
        "config_mutation_performed",
    ]

    for key in required:
        if key not in event:
            errors.append(f"missing_required_field:{key}")

    if event.get("phase") != PHASE:
        errors.append("phase_must_be_2.32")

    if event.get("mode") != MODE:
        errors.append("mode_must_be_dry_run_journal")

    for key in [
        "execution_allowed",
        "journal_write_performed",
        "live_source_reads_performed",
        "live_backup_writes_performed",
        "executor_dispatch_performed",
        "service_mutation_performed",
        "config_mutation_performed",
    ]:
        if event.get(key) is not False:
            errors.append(f"{key}_must_be_false")

    if event.get("fail_closed") is not True:
        errors.append("fail_closed_must_be_true")

    return errors


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate Phase 2.32 dry-run journal event JSON."
    )
    parser.add_argument("--manifest-file", help="Manifest JSON file. Defaults to stdin.")
    parser.add_argument("--validation-file", help="Optional validation report JSON file.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest = load_json(args.manifest_file)
    validation = load_json(args.validation_file) if args.validation_file else None

    event = build_event(manifest, validation)
    errors = validate_event(event)

    event["event_validation_result"] = "PASS" if not errors else "FAIL"
    event["event_validation_errors"] = errors

    print(json.dumps(event, indent=2, sort_keys=True))

    return 0 if not errors else 2


if __name__ == "__main__":
    raise SystemExit(main())
