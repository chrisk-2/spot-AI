#!/usr/bin/env python3
"""
Phase 2.31C dry-run backup manifest validator.

Reads manifest JSON from stdin or --file.
Writes validation report JSON to stdout only.

No live reads.
No live writes.
No executor dispatch.
No service/config mutation.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


APPROVED_BACKUP_ROOT = "/mnt/collective/backups"
PHASE = "2.31"
MODE = "dry_run"


REQUIRED_FIELDS = [
    "manifest_version",
    "timestamp_utc",
    "phase",
    "mode",
    "request_id",
    "target",
    "service",
    "risk_class",
    "requested_paths",
    "proposed_backup_root",
    "proposed_backup_path",
    "would_create_directories",
    "would_collect_files",
    "would_write_metadata",
    "would_write_checksums",
    "would_write_journal",
    "validation_plan",
    "rollback_plan_required",
    "execution_allowed",
    "fail_closed",
    "safety_assertions",
]


REQUIRED_VALIDATORS = [
    "schema_validator",
    "required_field_validator",
    "phase_boundary_validator",
    "no_live_read_validator",
    "no_live_write_validator",
    "no_executor_dispatch_validator",
    "backup_root_policy_validator",
    "requested_path_allowlist_validator",
    "journal_shape_validator",
    "rollback_requirement_validator",
    "review_requirement_validator",
]


REQUIRED_SAFETY_ASSERTIONS = {
    "live_source_reads_performed": False,
    "live_backup_writes_performed": False,
    "executor_dispatch_performed": False,
    "service_mutation_performed": False,
    "config_mutation_performed": False,
}


def load_manifest(path: str | None) -> dict:
    try:
        if path:
            return json.loads(Path(path).read_text())
        return json.loads(sys.stdin.read())
    except json.JSONDecodeError as exc:
        raise SystemExit(f"ERROR: invalid JSON: {exc}") from exc


def validate_manifest(manifest: dict) -> dict:
    errors: list[str] = []
    warnings: list[str] = []

    for key in REQUIRED_FIELDS:
        if key not in manifest:
            errors.append(f"missing_required_field:{key}")

    if manifest.get("phase") != PHASE:
        errors.append("phase_must_be_2.31")

    if manifest.get("mode") != MODE:
        errors.append("mode_must_be_dry_run")

    if manifest.get("execution_allowed") is not False:
        errors.append("execution_allowed_must_be_false")

    if manifest.get("fail_closed") is not True:
        errors.append("fail_closed_must_be_true")

    if manifest.get("rollback_plan_required") is not True:
        errors.append("rollback_plan_required_must_be_true")

    root = manifest.get("proposed_backup_root")
    path = manifest.get("proposed_backup_path")

    if root != APPROVED_BACKUP_ROOT:
        errors.append("backup_root_not_approved")

    if not isinstance(path, str) or not path.startswith(f"{APPROVED_BACKUP_ROOT}/"):
        errors.append("proposed_backup_path_outside_approved_root")

    requested_paths = manifest.get("requested_paths")
    if not isinstance(requested_paths, list) or not requested_paths:
        errors.append("requested_paths_must_be_non_empty_list")
    else:
        for item in requested_paths:
            if not isinstance(item, str) or not item.startswith("/"):
                errors.append(f"requested_path_not_absolute:{item}")

    validation_plan = manifest.get("validation_plan")
    if not isinstance(validation_plan, list):
        errors.append("validation_plan_must_be_list")
    else:
        missing_validators = sorted(set(REQUIRED_VALIDATORS) - set(validation_plan))
        for validator in missing_validators:
            errors.append(f"missing_validator:{validator}")

    assertions = manifest.get("safety_assertions")
    if not isinstance(assertions, dict):
        errors.append("safety_assertions_must_be_object")
    else:
        for key, expected in REQUIRED_SAFETY_ASSERTIONS.items():
            if assertions.get(key) is not expected:
                errors.append(f"safety_assertion_failed:{key}")

    for bool_field in [
        "would_write_metadata",
        "would_write_checksums",
        "would_write_journal",
    ]:
        if manifest.get(bool_field) is not True:
            errors.append(f"{bool_field}_must_be_true")

    for list_field in [
        "would_create_directories",
        "would_collect_files",
    ]:
        if not isinstance(manifest.get(list_field), list):
            errors.append(f"{list_field}_must_be_list")

    return {
        "validator": "spot-backup-dry-run-validate",
        "phase": PHASE,
        "mode": MODE,
        "validation_result": "PASS" if not errors else "FAIL",
        "errors": errors,
        "warnings": warnings,
        "execution_allowed": False,
        "fail_closed": True,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate Phase 2.31 dry-run backup manifest."
    )
    parser.add_argument("--file", help="Manifest JSON file. Defaults to stdin.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest = load_manifest(args.file)
    report = validate_manifest(manifest)

    print(json.dumps(report, indent=2, sort_keys=True))

    return 0 if report["validation_result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
