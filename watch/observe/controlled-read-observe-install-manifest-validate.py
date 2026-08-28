#!/usr/bin/env python3
"""Validate a K21C controlled read/observe installation manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

SCHEMA = "spot_controlled_read_observe_install_manifest_v1"
STATUS = "READY_FOR_SEPARATELY_AUTHORIZED_INSTALLATION"

FILE_MAP = {
    "watch/observe/controlled-read-observe.py": (
        "/usr/local/lib/spot/observe/controlled-read-observe.py",
        "0755",
    ),
    "watch/observe/controlled_read_observe_validation_v1.py": (
        "/usr/local/lib/spot/observe/"
        "controlled_read_observe_validation_v1.py",
        "0755",
    ),
    "watch/observe/controlled-read-observe-request-validate.py": (
        "/usr/local/lib/spot/observe/"
        "controlled-read-observe-request-validate.py",
        "0755",
    ),
    "watch/observe/controlled-read-observe-evidence-validate.py": (
        "/usr/local/lib/spot/observe/"
        "controlled-read-observe-evidence-validate.py",
        "0755",
    ),
    "watch/observe/controlled-read-observe-allowlist-v1.json": (
        "/etc/spot/observe/controlled-read-observe-allowlist-v1.json",
        "0644",
    ),
    "watch/observe/controlled-read-observe-request-schema-v1.json": (
        "/etc/spot/observe/"
        "controlled-read-observe-request-schema-v1.json",
        "0644",
    ),
    "watch/observe/controlled-read-observe-evidence-schema-v1.json": (
        "/etc/spot/observe/"
        "controlled-read-observe-evidence-schema-v1.json",
        "0644",
    ),
    "watch/observe/controlled-read-observe.service": (
        "/etc/systemd/system/spot-controlled-read-observe.service",
        "0644",
    ),
}

TOP_LEVEL = {
    "schema",
    "manifest_id",
    "generated_at",
    "host",
    "repository_head",
    "authorization",
    "review",
    "backup",
    "rollback",
    "files",
    "runtime",
    "planned_service_state",
    "governance",
    "status",
}

SHA_PATTERN = re.compile(r"^[a-f0-9]{64}$")
HEAD_PATTERN = re.compile(r"^[a-f0-9]{40}$")
MANIFEST_PATTERN = re.compile(
    r"^INSTALL-POST239-K21C-[A-Za-z0-9._:-]{8,128}$"
)
AUTH_PATH_PATTERN = re.compile(
    r"^watch/review/bundles/"
    r"AUTH-POST239-K21C-INSTALLATION-[A-Za-z0-9._:-]+\.json$"
)
REVIEW_PATH_PATTERN = re.compile(
    r"^watch/review/bundles/"
    r"POST239-K21C-[A-Za-z0-9._:-]+-PASS-[A-Za-z0-9._:-]+\.json$"
)
BACKUP_PATH_PATTERN = re.compile(
    r"^/mnt/collective/backups/spot-core/post239-k21c/"
    r"[A-Za-z0-9._:/-]+\.json$"
)


class ManifestError(ValueError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ManifestError(message)


def exact_keys(value: Any, keys: set[str], label: str) -> dict[str, Any]:
    require(isinstance(value, dict), f"{label} must be an object")
    actual = set(value)
    require(actual == keys, f"{label} fields mismatch: {sorted(actual ^ keys)}")
    return value


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_manifest(
    manifest: dict[str, Any],
    repository: Path,
    verify_references: bool = True,
) -> None:
    exact_keys(manifest, TOP_LEVEL, "manifest")

    require(manifest["schema"] == SCHEMA, "bad schema")
    require(
        isinstance(manifest["manifest_id"], str)
        and MANIFEST_PATTERN.fullmatch(manifest["manifest_id"]) is not None,
        "bad manifest_id",
    )
    require(isinstance(manifest["generated_at"], str), "bad generated_at")
    try:
        datetime.fromisoformat(
            manifest["generated_at"].replace("Z", "+00:00")
        )
    except ValueError as exc:
        raise ManifestError("bad generated_at") from exc

    require(manifest["host"] == "spot-core", "bad host")
    require(
        isinstance(manifest["repository_head"], str)
        and HEAD_PATTERN.fullmatch(manifest["repository_head"]) is not None,
        "bad repository_head",
    )
    require(manifest["status"] == STATUS, "bad status")

    authorization = exact_keys(
        manifest["authorization"],
        {
            "authorization_id",
            "record_path",
            "record_sha256",
            "system_path_installation_authorized",
        },
        "authorization",
    )
    require(
        isinstance(authorization["authorization_id"], str)
        and len(authorization["authorization_id"]) >= 8,
        "bad authorization_id",
    )
    require(
        AUTH_PATH_PATTERN.fullmatch(authorization["record_path"]) is not None,
        "bad authorization record path",
    )
    require(
        authorization["system_path_installation_authorized"] is False,
        "system-path installation authority expanded",
    )
    require(
        SHA_PATTERN.fullmatch(authorization["record_sha256"]) is not None,
        "bad authorization record SHA-256",
    )

    review = exact_keys(
        manifest["review"],
        {"review_pass_path", "review_pass_sha256", "verdict"},
        "review",
    )
    require(
        REVIEW_PATH_PATTERN.fullmatch(review["review_pass_path"]) is not None,
        "bad review record path",
    )
    require(review["verdict"] == "PASS", "review verdict is not PASS")
    require(
        SHA_PATTERN.fullmatch(review["review_pass_sha256"]) is not None,
        "bad review SHA-256",
    )

    backup = exact_keys(
        manifest["backup"],
        {
            "backup_manifest_id",
            "backup_manifest_path",
            "backup_manifest_sha256",
            "backup_verified",
            "backup_binding_id",
            "backup_binding_verified",
        },
        "backup",
    )
    require(
        isinstance(backup["backup_manifest_id"], str)
        and len(backup["backup_manifest_id"]) >= 8,
        "bad backup manifest ID",
    )
    require(
        BACKUP_PATH_PATTERN.fullmatch(backup["backup_manifest_path"])
        is not None,
        "bad backup manifest path",
    )
    require(
        isinstance(backup["backup_binding_id"], str)
        and len(backup["backup_binding_id"]) >= 8,
        "bad backup binding ID",
    )
    require(backup["backup_verified"] is True, "backup is not verified")
    require(
        backup["backup_binding_verified"] is True,
        "backup binding is not verified",
    )
    require(
        SHA_PATTERN.fullmatch(backup["backup_manifest_sha256"]) is not None,
        "bad backup manifest SHA-256",
    )

    rollback = exact_keys(
        manifest["rollback"],
        {
            "rollback_document",
            "rollback_document_sha256",
            "rollback_defined",
            "rollback_binding_id",
            "rollback_binding_verified",
        },
        "rollback",
    )
    require(
        rollback["rollback_document"]
        == "watch/observe/controlled-read-observe-install-rollback.md",
        "unexpected rollback document",
    )
    require(
        isinstance(rollback["rollback_binding_id"], str)
        and len(rollback["rollback_binding_id"]) >= 8,
        "bad rollback binding ID",
    )
    require(rollback["rollback_defined"] is True, "rollback is not defined")
    require(
        rollback["rollback_binding_verified"] is True,
        "rollback binding is not verified",
    )
    require(
        SHA_PATTERN.fullmatch(rollback["rollback_document_sha256"]) is not None,
        "bad rollback document SHA-256",
    )

    files = manifest["files"]
    require(isinstance(files, list), "files must be an array")
    require(len(files) == 8, "manifest must contain exactly eight files")

    observed_sources: set[str] = set()
    observed_destinations: set[str] = set()

    file_fields = {
        "source",
        "destination",
        "sha256",
        "mode",
        "owner",
        "group",
        "destination_preexisting",
    }

    for index, item in enumerate(files):
        item = exact_keys(item, file_fields, f"files[{index}]")
        source = item["source"]
        require(source in FILE_MAP, f"unexpected source: {source}")
        destination, mode = FILE_MAP[source]

        require(
            item["destination"] == destination,
            f"destination mismatch for {source}",
        )
        require(item["mode"] == mode, f"mode mismatch for {source}")
        require(item["owner"] == "root", f"owner mismatch for {source}")
        require(item["group"] == "root", f"group mismatch for {source}")
        require(
            isinstance(item["destination_preexisting"], bool),
            f"bad destination_preexisting for {source}",
        )
        require(
            SHA_PATTERN.fullmatch(item["sha256"]) is not None,
            f"bad source SHA-256 for {source}",
        )
        require(source not in observed_sources, f"duplicate source: {source}")
        require(
            destination not in observed_destinations,
            f"duplicate destination: {destination}",
        )

        source_path = repository / source
        require(source_path.is_file(), f"source missing: {source}")
        require(
            sha256_file(source_path) == item["sha256"],
            f"source hash mismatch: {source}",
        )

        observed_sources.add(source)
        observed_destinations.add(destination)

    require(observed_sources == set(FILE_MAP), "source set is incomplete")

    runtime = exact_keys(
        manifest["runtime"],
        {
            "request_file",
            "request_file_mode",
            "evidence_directory",
            "evidence_directory_mode",
            "runtime_owner",
        },
        "runtime",
    )
    require(
        runtime
        == {
            "request_file":
                "/var/lib/spot/controlled-read-observe/request.json",
            "request_file_mode": "0600",
            "evidence_directory":
                "/var/lib/spot/controlled-read-observe/evidence",
            "evidence_directory_mode": "0700",
            "runtime_owner": "root",
        },
        "runtime boundary mismatch",
    )

    planned = exact_keys(
        manifest["planned_service_state"],
        {
            "daemon_reload_planned",
            "service_activation_planned",
            "timer_installation_planned",
            "observer_enabled",
            "observer_scheduled",
        },
        "planned_service_state",
    )
    require(
        planned["daemon_reload_planned"] is False,
        "daemon-reload planning authority expanded",
    )
    for field in (
        "service_activation_planned",
        "timer_installation_planned",
        "observer_enabled",
        "observer_scheduled",
    ):
        require(planned[field] is False, f"unsafe planned state: {field}")

    governance = exact_keys(
        manifest["governance"],
        {
            "spot_core_sole_authority",
            "worker_self_apply_allowed",
            "activation_authorized",
            "scheduling_authorized",
            "production_observation_authorized",
            "live_executor_enabled",
            "execution_allowed",
            "mutation_authority",
        },
        "governance",
    )
    require(
        governance["spot_core_sole_authority"] is True,
        "Spot Core sole authority missing",
    )
    for field in (
        "worker_self_apply_allowed",
        "activation_authorized",
        "scheduling_authorized",
        "production_observation_authorized",
        "live_executor_enabled",
        "execution_allowed",
        "mutation_authority",
    ):
        require(governance[field] is False, f"unsafe governance state: {field}")

    if verify_references:
        references = (
            (
                repository / authorization["record_path"],
                authorization["record_sha256"],
                "authorization",
            ),
            (
                repository / review["review_pass_path"],
                review["review_pass_sha256"],
                "review",
            ),
            (
                Path(backup["backup_manifest_path"]),
                backup["backup_manifest_sha256"],
                "backup manifest",
            ),
            (
                repository / rollback["rollback_document"],
                rollback["rollback_document_sha256"],
                "rollback document",
            ),
        )

        for path, expected_sha, label in references:
            require(path.is_file(), f"{label} missing: {path}")
            require(
                sha256_file(path) == expected_sha,
                f"{label} hash mismatch",
            )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate a K21C installation manifest."
    )
    parser.add_argument("manifest", type=Path)
    parser.add_argument(
        "--repository",
        type=Path,
        default=Path.cwd(),
    )
    args = parser.parse_args()

    try:
        payload = json.loads(args.manifest.read_text(encoding="utf-8"))
        require(isinstance(payload, dict), "manifest must be an object")
        validate_manifest(payload, args.repository.resolve())
    except (OSError, json.JSONDecodeError, ManifestError) as exc:
        print(f"[DENY] invalid K21C installation manifest: {exc}", file=sys.stderr)
        return 2

    print("[PASS] K21C installation manifest valid")
    print("system_path_installation_authorized=false")
    print("activation_authorized=false")
    print("scheduling_authorized=false")
    print("production_observation_authorized=false")
    print("execution_allowed=false")
    print("mutation_authority=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
