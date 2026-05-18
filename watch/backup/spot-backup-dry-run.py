#!/usr/bin/env python3
"""
Phase 2.31B dry-run backup manifest generator.

This script does not:
- read live source files
- create backup directories
- write backup artifacts
- dispatch execution
- mutate services or config

It prints a dry-run manifest to stdout only.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import PurePosixPath
from uuid import uuid4


APPROVED_BACKUP_ROOT = "/mnt/collective/backups"
PHASE = "2.31"
MODE = "dry_run"


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def fail(message: str) -> None:
    raise SystemExit(f"ERROR: {message}")


def normalize_posix_path(path: str) -> str:
    if not path.startswith("/"):
        fail(f"requested path must be absolute: {path}")
    return str(PurePosixPath(path))


def build_manifest(args: argparse.Namespace) -> dict:
    requested_paths = [normalize_posix_path(p) for p in args.requested_path]

    request_id = args.request_id or f"dryrun-{uuid4()}"
    proposed_backup_root = args.proposed_backup_root.rstrip("/")
    proposed_backup_path = (
        f"{proposed_backup_root}/{args.target}/{args.service}/DRYRUN-{request_id}"
    )

    validators = [
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

    return {
        "manifest_version": "1.0",
        "timestamp_utc": utc_now(),
        "phase": PHASE,
        "mode": MODE,
        "request_id": request_id,
        "target": args.target,
        "service": args.service,
        "risk_class": args.risk_class,
        "operator_intent": args.operator_intent,
        "review_id": args.review_id,
        "requested_paths": requested_paths,
        "proposed_backup_root": proposed_backup_root,
        "proposed_backup_path": proposed_backup_path,
        "would_create_directories": [
            proposed_backup_path,
        ],
        "would_collect_files": requested_paths,
        "would_write_metadata": True,
        "would_write_checksums": True,
        "would_write_journal": True,
        "validation_plan": validators,
        "rollback_plan_required": True,
        "execution_allowed": False,
        "fail_closed": True,
        "safety_assertions": {
            "live_source_reads_performed": False,
            "live_backup_writes_performed": False,
            "executor_dispatch_performed": False,
            "service_mutation_performed": False,
            "config_mutation_performed": False,
        },
    }


def validate_manifest(manifest: dict) -> list[str]:
    errors: list[str] = []

    required = [
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

    for key in required:
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

    root = str(manifest.get("proposed_backup_root", ""))
    path = str(manifest.get("proposed_backup_path", ""))
    if root != APPROVED_BACKUP_ROOT:
        errors.append("backup_root_not_approved")

    if not path.startswith(f"{APPROVED_BACKUP_ROOT}/"):
        errors.append("proposed_backup_path_outside_approved_root")

    assertions = manifest.get("safety_assertions", {})
    for key, expected in {
        "live_source_reads_performed": False,
        "live_backup_writes_performed": False,
        "executor_dispatch_performed": False,
        "service_mutation_performed": False,
        "config_mutation_performed": False,
    }.items():
        if assertions.get(key) is not expected:
            errors.append(f"safety_assertion_failed:{key}")

    if manifest.get("rollback_plan_required") is not True:
        errors.append("rollback_plan_required_must_be_true")

    return errors


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate Phase 2.31 dry-run backup manifest."
    )
    parser.add_argument("--target", required=True)
    parser.add_argument("--service", required=True)
    parser.add_argument(
        "--risk-class",
        required=True,
        choices=["low", "medium", "high"],
    )
    parser.add_argument(
        "--requested-path",
        action="append",
        required=True,
        help="Absolute path that would be backed up in a future non-dry-run phase. Repeatable.",
    )
    parser.add_argument(
        "--proposed-backup-root",
        default=APPROVED_BACKUP_ROOT,
    )
    parser.add_argument("--request-id")
    parser.add_argument("--operator-intent", default="dry-run backup planning")
    parser.add_argument("--review-id")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    manifest = build_manifest(args)
    errors = validate_manifest(manifest)

    manifest["validation_result"] = "PASS" if not errors else "FAIL"
    manifest["validation_errors"] = errors

    print(json.dumps(manifest, indent=2, sort_keys=True))

    return 0 if not errors else 2


if __name__ == "__main__":
    raise SystemExit(main())
