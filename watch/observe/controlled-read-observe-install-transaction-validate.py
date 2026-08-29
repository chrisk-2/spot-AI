#!/usr/bin/env python3
"""Fail-closed validation for a future K21D installation transaction."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

SCHEMA_NAME = "starfleet.post239.k21d_install_transaction.v1"
STATUS = "READY_FOR_SEPARATELY_AUTHORIZED_INSTALLATION_ONLY"
SHA = re.compile(r"^[a-f0-9]{64}$")
HEAD = re.compile(r"^[a-f0-9]{40}$")

FILE_MAP = [
    (
        'watch/observe/controlled-read-observe.py',
        '/usr/local/lib/spot/observe/controlled-read-observe.py',
        '0755',
    ),
    (
        'watch/observe/controlled_read_observe_validation_v1.py',
        '/usr/local/lib/spot/observe/controlled_read_observe_validation_v1.py',
        '0755',
    ),
    (
        'watch/observe/controlled-read-observe-request-validate.py',
        '/usr/local/lib/spot/observe/controlled-read-observe-request-validate.py',
        '0755',
    ),
    (
        'watch/observe/controlled-read-observe-evidence-validate.py',
        '/usr/local/lib/spot/observe/controlled-read-observe-evidence-validate.py',
        '0755',
    ),
    (
        'watch/observe/controlled-read-observe-allowlist-v1.json',
        '/etc/spot/observe/controlled-read-observe-allowlist-v1.json',
        '0644',
    ),
    (
        'watch/observe/controlled-read-observe-request-schema-v1.json',
        '/etc/spot/observe/controlled-read-observe-request-schema-v1.json',
        '0644',
    ),
    (
        'watch/observe/controlled-read-observe-evidence-schema-v1.json',
        '/etc/spot/observe/controlled-read-observe-evidence-schema-v1.json',
        '0644',
    ),
    (
        'watch/observe/controlled-read-observe.service',
        '/etc/systemd/system/spot-controlled-read-observe.service',
        '0644',
    ),
]

class TransactionError(ValueError):
    """Transaction validation denial."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise TransactionError(message)


def exact(value: Any, keys: set[str], label: str) -> dict[str, Any]:
    require(isinstance(value, dict), f"{label} must be an object")
    require(set(value) == keys, f"{label} fields mismatch")
    return value


def digest(path: Path) -> str:
    value = hashlib.sha256()

    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(chunk)

    return value.hexdigest()


def timestamp(value: Any, label: str) -> datetime:
    require(isinstance(value, str), f"{label} must be a string")

    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise TransactionError(f"invalid {label}") from exc

    require(parsed.tzinfo is not None, f"{label} must include timezone")
    return parsed


def repo_path(repository: Path, value: Any, label: str) -> Path:
    require(isinstance(value, str), f"{label} must be a string")
    require(not value.startswith("/"), f"{label} must be repository-relative")

    resolved = (repository / value).resolve()
    require(
        resolved == repository or repository in resolved.parents,
        f"{label} escapes repository",
    )
    return resolved


def validate_transaction(
    payload: dict[str, Any],
    repository: Path,
    *,
    verify_references: bool = True,
) -> None:
    repository = repository.resolve()

    top = exact(
        payload,
        {
            "schema",
            "transaction_id",
            "generated_at",
            "expires_at",
            "host",
            "repository_head",
            "design_review",
            "operator_authorization",
            "backup",
            "rollback",
            "files",
            "planned_service_state",
            "governance",
            "status",
        },
        "transaction",
    )

    require(top["schema"] == SCHEMA_NAME, "wrong schema")
    require(top["host"] == "spot-core", "wrong host")
    require(
        isinstance(top["transaction_id"], str)
        and top["transaction_id"].startswith("INSTALL-POST239-K21D-"),
        "bad transaction ID",
    )
    require(
        isinstance(top["repository_head"], str)
        and HEAD.fullmatch(top["repository_head"]) is not None,
        "bad repository head",
    )
    require(top["status"] == STATUS, "bad transaction status")

    generated = timestamp(top["generated_at"], "generated_at")
    expires = timestamp(top["expires_at"], "expires_at")
    require(expires > generated, "authorization is not forward-expiring")

    review = exact(
        top["design_review"],
        {"record_path", "record_sha256", "verdict"},
        "design_review",
    )
    require(review["verdict"] == "PASS", "design review not PASS")
    require(
        isinstance(review["record_sha256"], str)
        and SHA.fullmatch(review["record_sha256"]) is not None,
        "bad design review digest",
    )
    review_path = repo_path(
        repository,
        review["record_path"],
        "design review path",
    )

    authorization = exact(
        top["operator_authorization"],
        {
            "authorization_id",
            "record_path",
            "record_sha256",
            "system_path_installation_authorized",
            "single_use",
            "consumed",
        },
        "operator_authorization",
    )
    require(
        isinstance(authorization["authorization_id"], str)
        and authorization["authorization_id"].startswith(
            "AUTH-POST239-K21D-INSTALLATION-"
        ),
        "bad installation authorization ID",
    )
    require(
        authorization["system_path_installation_authorized"] is True,
        "installation authorization absent",
    )
    require(authorization["single_use"] is True, "authorization not single-use")
    require(authorization["consumed"] is False, "authorization already consumed")
    require(
        isinstance(authorization["record_sha256"], str)
        and SHA.fullmatch(authorization["record_sha256"]) is not None,
        "bad authorization digest",
    )
    authorization_path = repo_path(
        repository,
        authorization["record_path"],
        "authorization path",
    )

    backup = exact(
        top["backup"],
        {
            "manifest_id",
            "manifest_path",
            "manifest_sha256",
            "binding_id",
            "verified",
        },
        "backup",
    )
    require(backup["verified"] is True, "backup is not verified")
    require(
        isinstance(backup["manifest_path"], str)
        and backup["manifest_path"].startswith(
            "/mnt/collective/backups/spot-core/post239-k21d/"
        ),
        "backup path outside fixed root",
    )
    require(
        isinstance(backup["manifest_sha256"], str)
        and SHA.fullmatch(backup["manifest_sha256"]) is not None,
        "bad backup manifest digest",
    )

    rollback = exact(
        top["rollback"],
        {
            "document_path",
            "document_sha256",
            "binding_id",
            "verified",
        },
        "rollback",
    )
    require(rollback["verified"] is True, "rollback is not verified")
    require(
        rollback["document_path"]
        == "watch/observe/controlled-read-observe-install-rollback.md",
        "wrong rollback document",
    )
    require(
        isinstance(rollback["document_sha256"], str)
        and SHA.fullmatch(rollback["document_sha256"]) is not None,
        "bad rollback digest",
    )
    rollback_path = repo_path(
        repository,
        rollback["document_path"],
        "rollback path",
    )

    files = top["files"]
    require(isinstance(files, list), "files must be an array")
    require(len(files) == 8, "transaction must contain exactly eight files")

    destinations: set[str] = set()

    for index, (entry, expected) in enumerate(zip(files, FILE_MAP), start=1):
        source, destination, mode = expected
        item = exact(
            entry,
            {
                "source",
                "destination",
                "source_sha256",
                "mode",
                "owner",
                "group",
                "destination_preexisting",
                "destination_type_before",
                "backup_sha256",
            },
            f"file {index}",
        )

        require(item["source"] == source, f"source mismatch at file {index}")
        require(
            item["destination"] == destination,
            f"destination mismatch at file {index}",
        )
        require(item["mode"] == mode, f"mode mismatch at file {index}")
        require(item["owner"] == "root", f"owner mismatch at file {index}")
        require(item["group"] == "root", f"group mismatch at file {index}")
        require(destination not in destinations, "duplicate destination")
        destinations.add(destination)

        require(
            isinstance(item["source_sha256"], str)
            and SHA.fullmatch(item["source_sha256"]) is not None,
            f"bad source digest at file {index}",
        )

        if item["destination_preexisting"] is True:
            require(
                item["destination_type_before"] == "regular",
                f"preexisting destination not regular at file {index}",
            )
            require(
                isinstance(item["backup_sha256"], str)
                and SHA.fullmatch(item["backup_sha256"]) is not None,
                f"missing backup digest at file {index}",
            )
        else:
            require(
                item["destination_preexisting"] is False,
                f"bad preexisting flag at file {index}",
            )
            require(
                item["destination_type_before"] == "absent",
                f"absent destination state mismatch at file {index}",
            )
            require(
                item["backup_sha256"] is None,
                f"absent destination has backup digest at file {index}",
            )

        if verify_references:
            source_path = repo_path(repository, source, f"source {index}")
            require(source_path.is_file(), f"source missing at file {index}")
            require(
                digest(source_path) == item["source_sha256"],
                f"source digest mismatch at file {index}",
            )

    planned = exact(
        top["planned_service_state"],
        {
            "daemon_reload_if_unit_changed",
            "unconditional_daemon_reload",
            "service_start_planned",
            "service_enablement_planned",
            "timer_installation_planned",
            "request_dispatch_planned",
            "production_observation_planned",
        },
        "planned_service_state",
    )
    require(
        planned["daemon_reload_if_unit_changed"] is True,
        "conditional daemon-reload control absent",
    )

    for field in (
        "unconditional_daemon_reload",
        "service_start_planned",
        "service_enablement_planned",
        "timer_installation_planned",
        "request_dispatch_planned",
        "production_observation_planned",
    ):
        require(planned[field] is False, f"unsafe planned state: {field}")

    governance = exact(
        top["governance"],
        {
            "spot_core_sole_authority",
            "worker_self_apply_allowed",
            "activation_authorized",
            "enablement_authorized",
            "scheduling_authorized",
            "production_observation_authorized",
            "service_action_authorized",
            "live_executor_enabled",
            "execution_allowed",
            "mutation_authority",
        },
        "governance",
    )
    require(
        governance["spot_core_sole_authority"] is True,
        "Spot Core authority missing",
    )

    for field in (
        "worker_self_apply_allowed",
        "activation_authorized",
        "enablement_authorized",
        "scheduling_authorized",
        "production_observation_authorized",
        "service_action_authorized",
        "live_executor_enabled",
        "execution_allowed",
        "mutation_authority",
    ):
        require(governance[field] is False, f"unsafe governance state: {field}")

    if verify_references:
        for path, expected_digest, label in (
            (review_path, review["record_sha256"], "design review"),
            (
                authorization_path,
                authorization["record_sha256"],
                "authorization",
            ),
            (rollback_path, rollback["document_sha256"], "rollback"),
        ):
            require(path.is_file(), f"{label} reference missing")
            require(digest(path) == expected_digest, f"{label} digest mismatch")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--transaction", type=Path, required=True)
    parser.add_argument("--repository", type=Path, default=Path.cwd())
    parser.add_argument(
        "--offline-no-reference-check",
        action="store_true",
    )
    args = parser.parse_args()

    try:
        payload = json.loads(args.transaction.read_text(encoding="utf-8"))
        require(isinstance(payload, dict), "transaction must be an object")
        validate_transaction(
            payload,
            args.repository,
            verify_references=not args.offline_no_reference_check,
        )
    except (OSError, json.JSONDecodeError, TransactionError) as exc:
        print(f"[DENY] invalid K21D transaction: {exc}", file=sys.stderr)
        return 2

    print("[PASS] K21D transaction valid")
    print("validation_only=true")
    print("installation_performed=false")
    print("daemon_reload_performed=false")
    print("activation_authorized=false")
    print("execution_allowed=false")
    print("mutation_authority=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
