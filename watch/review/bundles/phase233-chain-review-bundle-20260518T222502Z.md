# Phase 2.33 Complete Dry-Run Chain Review Bundle

Generated:
20260518T222502Z

Commit:
7c7dccb70633f486378691c36217e2b6daf14935

Validation:
[PASS] governance integrity

=== SUMMARY ===
pass=30 warn=0 fail=0
RESULT: PASS

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

# FILE: watch/backup/spot-backup-dry-run-validate.py

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

---

# FILE: watch/backup/spot-backup-dry-run-journal.py

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

---

# FILE: watch/backup/spot-backup-dry-run-chain.py

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

---

# TEST MANIFEST

{
  "execution_allowed": false,
  "fail_closed": true,
  "manifest_version": "1.0",
  "mode": "dry_run",
  "operator_intent": "dry-run backup planning",
  "phase": "2.31",
  "proposed_backup_path": "/mnt/collective/backups/spot-worker-01/ollama/DRYRUN-phase233-review-test-001",
  "proposed_backup_root": "/mnt/collective/backups",
  "request_id": "phase233-review-test-001",
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
  "timestamp_utc": "2026-05-18T22:25:02Z",
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
    "/mnt/collective/backups/spot-worker-01/ollama/DRYRUN-phase233-review-test-001"
  ],
  "would_write_checksums": true,
  "would_write_journal": true,
  "would_write_metadata": true
}

---

# TEST VALIDATION REPORT

{
  "errors": [],
  "execution_allowed": false,
  "fail_closed": true,
  "mode": "dry_run",
  "phase": "2.31",
  "validation_result": "PASS",
  "validator": "spot-backup-dry-run-validate",
  "warnings": []
}

---

# TEST JOURNAL EVENT

{
  "config_mutation_performed": false,
  "event_id": "dryrun-journal-8e001a04-988b-4d51-bf0d-0347a7a1055c",
  "event_type": "backup_dry_run_manifest_journal",
  "event_validation_errors": [],
  "event_validation_result": "PASS",
  "event_version": "1.0",
  "execution_allowed": false,
  "executor_dispatch_performed": false,
  "external_validation_errors": [],
  "external_validation_result": "PASS",
  "fail_closed": true,
  "journal_write_performed": false,
  "live_backup_writes_performed": false,
  "live_source_reads_performed": false,
  "manifest_mode": "dry_run",
  "manifest_phase": "2.31",
  "manifest_validation_result": "PASS",
  "mode": "dry_run_journal",
  "notes": [
    "stdout-only dry-run journal event",
    "no append to live journal",
    "no backup artifact writes",
    "no executor dispatch",
    "no mutation"
  ],
  "phase": "2.32",
  "proposed_backup_path": "/mnt/collective/backups/spot-worker-01/ollama/DRYRUN-phase233-review-test-001",
  "proposed_backup_root": "/mnt/collective/backups",
  "request_id": "phase233-review-test-001",
  "requested_paths": [
    "/etc/ollama"
  ],
  "risk_class": "low",
  "service": "ollama",
  "service_mutation_performed": false,
  "target": "spot-worker-01",
  "timestamp_utc": "2026-05-18T22:25:02Z"
}

---

# TEST CHAIN PACKAGE

{
  "artifacts": {
    "journal_file": "/tmp/tmp.tUPbmMa7Al",
    "journal_sha256": "a9cecdbf56c18ae1ad091c59ed6da31552c32018bb214cfdcf4008da157ecf8d",
    "manifest_file": "/tmp/tmp.TbU058Ewm3",
    "manifest_sha256": "2c0c25a4f04b26a633251a157256fdfd5d4fedc81fcdd4e0402d9813619e62e3",
    "validation_file": "/tmp/tmp.IgKiQbV2Se",
    "validation_sha256": "c1e824ecff9b5b1ebb801672ef5bb133fa6033fbbd665e8397883fa0d14386d9"
  },
  "chain_id": "dryrun-chain-a81438e0-148c-400e-b057-f307bc89a7d2",
  "chain_validation_errors": [],
  "chain_validation_result": "PASS",
  "chain_version": "1.0",
  "mode": "dry_run_chain",
  "phase": "2.33",
  "request_id": "phase233-review-test-001",
  "results": {
    "external_validation_result": "PASS",
    "journal_event_validation_result": "PASS",
    "manifest_validation_result": "PASS"
  },
  "review_requirements": {
    "execution_allowed_after_review": false,
    "review_authority": "proposal_review_only",
    "worker05_grounded_review_required": true
  },
  "risk_class": "low",
  "safety_assertions": {
    "config_mutation_performed": false,
    "execution_allowed": false,
    "executor_dispatch_performed": false,
    "fail_closed": true,
    "journal_append_performed": false,
    "live_backup_writes_performed": false,
    "live_source_reads_performed": false,
    "service_mutation_performed": false
  },
  "service": "ollama",
  "target": "spot-worker-01",
  "timestamp_utc": "2026-05-18T22:25:02Z"
}
