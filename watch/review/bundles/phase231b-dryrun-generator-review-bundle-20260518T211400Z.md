# Phase 2.31B Dry-Run Generator Review Bundle

Generated:
20260518T211400Z

Commit:
a25df3e9edaf1836e4a55ed78790c40297548091

Validation:
[PASS] governance integrity

=== SUMMARY ===
pass=30 warn=0 fail=0
RESULT: PASS

---

# FILE: watch/backup/PHASE231-DRY-RUN-BACKUP-WRAPPER-SPEC.md

# Phase 2.31 — Dry-Run Backup Wrapper Specification

## Status

Design/specification only.

No live backup writes.
No live source reads.
No service restarts.
No config writes.
No executor dispatch.
No mutation.

## Goal

Define the dry-run backup wrapper contract that will later allow Spot Core to prove backup intent, policy gates, manifest shape, validation sequencing, and journal output without touching live target systems.

## Scope

Phase 2.31 may define:

- dry-run wrapper interface
- dry-run request schema
- dry-run manifest schema
- simulated backup artifact records
- deterministic validator sequence
- fail-closed behavior
- review bundle requirements
- expected journal shape
- future implementation constraints

Phase 2.31 may not perform:

- live source reads
- live hashing of production files
- live backup directory creation
- service mutation
- config mutation
- executor dispatch
- rollback execution

## Dry-Run Wrapper Contract

A dry-run backup wrapper receives:

- request_id
- target
- service
- risk_class
- requested_paths
- proposed_backup_root
- phase
- operator_intent
- review_id if available

The wrapper returns a dry-run manifest only.

The wrapper must not read requested_paths from the target.
The wrapper must not create backup artifacts.
The wrapper must not bind a backup to execution.
The wrapper must not authorize execution.

## Dry-Run Manifest Required Fields

- manifest_version
- timestamp_utc
- phase
- mode
- request_id
- target
- service
- risk_class
- requested_paths
- proposed_backup_root
- proposed_backup_path
- would_create_directories
- would_collect_files
- would_write_metadata
- would_write_checksums
- would_write_journal
- validation_plan
- rollback_plan_required
- execution_allowed
- fail_closed

## Required Static Validators

The dry-run output is valid only if all static validators pass:

- schema validator
- required field validator
- phase boundary validator
- no-live-read validator
- no-live-write validator
- no-executor-dispatch validator
- backup root policy validator
- requested path allowlist validator
- journal shape validator
- rollback requirement validator
- review requirement validator

## PASS Conditions

Phase 2.31 dry-run validation passes only when:

- manifest is valid JSON
- mode is dry_run
- phase is 2.31
- execution_allowed is false
- fail_closed is true
- no live source read occurred
- no live backup write occurred
- no service/config mutation occurred
- proposed backup path is under approved backup root
- rollback requirement is declared
- journal shape is declared
- all static validators pass

## FAIL Conditions

Dry-run validation fails if:

- manifest is missing required fields
- execution_allowed is true
- mode is not dry_run
- live source paths are read
- backup artifacts are created
- executor dispatch is attempted
- backup root is outside approved policy
- rollback requirement is absent
- validation plan is absent
- journal shape is absent

## Fail-Closed Behavior

Any failed validator must:

- block progression
- prevent backup binding
- prevent executor dispatch
- record failure reason in dry-run output
- require review before retry

## Review Requirements

Worker-05 must review Phase 2.31 design/spec changes before any implementation.

Worker-05 review must verify:

- dry-run only
- no live mutation
- no executor dispatch
- required fields present
- validators defined
- fail-closed behavior defined
- rollback and journal requirements preserved

## Phase Exit Criteria

Phase 2.31 exits only when:

- dry-run wrapper spec is committed
- grounded Worker-05 review returns PASS
- spot validate returns PASS
- no live mutation has occurred

---

# FILE: watch/backup/spot-backup-dry-run.py

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

---

# DRY-RUN TEST OUTPUT

{
  "execution_allowed": false,
  "fail_closed": true,
  "manifest_version": "1.0",
  "mode": "dry_run",
  "operator_intent": "dry-run backup planning",
  "phase": "2.31",
  "proposed_backup_path": "/mnt/collective/backups/spot-worker-01/ollama/DRYRUN-phase231b-review-test-001",
  "proposed_backup_root": "/mnt/collective/backups",
  "request_id": "phase231b-review-test-001",
  "requested_paths": [
    "/etc/ollama"
  ],
  "review_id": null,
  "risk_class": "low",
  "rollback_plan_required": true,
  "safety_assertions": {
    "config_mutation_performed": false,
    "executor_dispatch_performed": false,
    "live_backup_writes_performed": false,
    "live_source_reads_performed": false,
    "service_mutation_performed": false
  },
  "service": "ollama",
  "target": "spot-worker-01",
  "timestamp_utc": "2026-05-18T21:14:24Z",
  "validation_errors": [],
  "validation_plan": [
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
    "review_requirement_validator"
  ],
  "validation_result": "PASS",
  "would_collect_files": [
    "/etc/ollama"
  ],
  "would_create_directories": [
    "/mnt/collective/backups/spot-worker-01/ollama/DRYRUN-phase231b-review-test-001"
  ],
  "would_write_checksums": true,
  "would_write_journal": true,
  "would_write_metadata": true
}
