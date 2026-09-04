#!/usr/bin/env python3
"""Validate one Post-2.39 K21D scoped NFS storage transaction.

The validator is deliberately strict.  It accepts only the reviewed two-mount
boundary, the fixed preservation set, a Worker-05 PASS, and a separate
single-use operator authorization.  Validation never performs a mount or a
system mutation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import stat
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


TRANSACTION_SCHEMA = "starfleet.post239.k21d_scoped_nfs_storage_transaction.v1"
AUTHORIZATION_SCHEMA = "starfleet.post239.k21d_scoped_nfs_storage_authorization.v1"
TRANSACTION_STATUS = "READY_FOR_SEPARATELY_AUTHORIZED_STORAGE_TRANSACTION_ONLY"
AUTHORIZATION_STATUS = "AUTHORIZED_FOR_SINGLE_SCOPED_NFS_STORAGE_TRANSACTION_ONLY"
RUNTIME_DRIFT = "starfleet-ui/public/status.json"
FIXED_REPOSITORY = Path("/home/ogre/spot-stack")
SHA = re.compile(r"[a-f0-9]{64}")
HEAD = re.compile(r"[a-f0-9]{40}")
TRANSACTION_ID = re.compile(r"STORAGE-POST239-K21D-[A-Za-z0-9._:-]{8,128}")
AUTHORIZATION_ID = re.compile(r"AUTH-STORAGE-POST239-K21D-[A-Za-z0-9._:-]{8,128}")
BACKUP_ID = re.compile(r"BACKUP-STORAGE-POST239-K21D-[A-Za-z0-9._:-]{8,128}")
BACKUP_BINDING_ID = re.compile(
    r"BACKUP-BINDING-STORAGE-POST239-K21D-[A-Za-z0-9._:-]{8,128}"
)
ROLLBACK_BINDING_ID = re.compile(
    r"ROLLBACK-BINDING-STORAGE-POST239-K21D-[A-Za-z0-9._:-]{8,128}"
)
IMPLEMENTATION_REVIEW_ID = re.compile(
    r"REVIEW-POST239-K21D-SCOPED-NFS-STORAGE-IMPLEMENTATION-"
    r"[A-Za-z0-9._:-]{8,128}"
)

DESIGN_REVIEW = {
    "design_path": "watch/storage/POST239-K21D-SCOPED-NFS-STORAGE-DESIGN.md",
    "design_sha256": "e127b728a8604d71683a53f7df59db56550f1515468beec337840abf69e84e99",
    "contract_path": "watch/storage/post239-k21d-scoped-nfs-storage-design-v1.json",
    "contract_sha256": "78b8fe437bb60a554fb334bd479912b8453be6577a78de9e7a3cffa09fa0698f",
    "bundle_path": (
        "watch/review/bundles/"
        "REVIEW-POST239-K21D-SCOPED-NFS-STORAGE-20260902T230902Z.md"
    ),
    "bundle_sha256": "3c46fdbff23d5ab27ced5d5bd7ffb32640129ebb0e271d2491f33fdaaa734238",
    "result_path": (
        "watch/review/bundles/"
        "REVIEW-POST239-K21D-SCOPED-NFS-STORAGE-20260902T230902Z.worker05.json"
    ),
    "result_sha256": "f358a1e2710e19da9ed07953030104ea0109e9fe5d4db8f77a95e9d0e86c59d5",
    "review_id": "REVIEW-POST239-K21D-SCOPED-NFS-STORAGE-20260902T230902Z",
    "reviewer": "spot-worker-05",
    "model": "deepseek-r1:32b",
    "verdict": "PASS",
}

IMPLEMENTATION_PATHS = (
    "watch/storage/post239-k21d-scoped-nfs-storage.py",
    "watch/storage/post239-k21d-scoped-nfs-storage-validate.py",
    "watch/storage/post239-k21d-scoped-nfs-storage-transaction-schema-v1.json",
    "watch/storage/post239-k21d-scoped-nfs-storage-authorization-schema-v1.json",
    "watch/storage/post239-k21d-scoped-nfs-storage-execution-test.py",
    "watch/storage/post239-k21d-scoped-nfs-storage-failure-test.py",
    "watch/storage/post239-k21d-scoped-nfs-storage-rollback.md",
    "watch/storage/post239-k21d-backup.mount",
    "watch/storage/post239-k21d-evidence.mount",
)

MOUNTS = (
    {
        "purpose": "backup",
        "source": (
            "192.168.50.10:/volume1/spotvault/"
            "backups/spot-core/post239-k21d"
        ),
        "target": "/mnt/collective/backups/spot-core/post239-k21d",
        "unit_name": (
            "mnt-collective-backups-spot\\x2dcore-post239\\x2dk21d.mount"
        ),
        "template_path": "watch/storage/post239-k21d-backup.mount",
        "installed_path": (
            "/etc/systemd/system/"
            "mnt-collective-backups-spot\\x2dcore-post239\\x2dk21d.mount"
        ),
    },
    {
        "purpose": "evidence",
        "source": (
            "192.168.50.10:/volume1/spotvault/"
            "logs/spot/actions/post239-k21d"
        ),
        "target": "/mnt/collective/logs/spot/actions/post239-k21d",
        "unit_name": (
            "mnt-collective-logs-spot-actions-post239\\x2dk21d.mount"
        ),
        "template_path": "watch/storage/post239-k21d-evidence.mount",
        "installed_path": (
            "/etc/systemd/system/"
            "mnt-collective-logs-spot-actions-post239\\x2dk21d.mount"
        ),
    },
)

PRESERVED_OBJECTS = (
    {
        "kind": "file",
        "source_path": (
            "/mnt/collective/backups/spot-core/post239-k21d/"
            "BACKUP-POST239-K21D-20260902T135309Z.json"
        ),
        "destination_relative": (
            "backups/spot-core/post239-k21d/"
            "BACKUP-POST239-K21D-20260902T135309Z.json"
        ),
        "sha256": "6154e049e83dc903cae4edb68c9b09812c896d0442dceff1e35be71780271ffd",
        "mode": "0400",
        "uid": 0,
        "gid": 0,
    },
    {
        "kind": "directory",
        "source_path": (
            "/mnt/collective/backups/spot-core/post239-k21d/"
            "BACKUP-POST239-K21D-20260902T135309Z-files"
        ),
        "destination_relative": (
            "backups/spot-core/post239-k21d/"
            "BACKUP-POST239-K21D-20260902T135309Z-files"
        ),
        "sha256": None,
        "mode": "0700",
        "uid": 0,
        "gid": 0,
    },
    {
        "kind": "file",
        "source_path": (
            "/mnt/collective/logs/spot/actions/post239-k21d/"
            "INSTALL-POST239-K21D-20260902T135309Z.json"
        ),
        "destination_relative": (
            "logs/spot/actions/post239-k21d/"
            "INSTALL-POST239-K21D-20260902T135309Z.json"
        ),
        "sha256": "89585870e08664b7fe889524f20c7dd4c89411761976b683d3d1458bdeeca30b",
        "mode": "0400",
        "uid": 0,
        "gid": 0,
    },
)

AUTHORIZATION_SCOPE = {
    "backup_creation_authorized": True,
    "backup_binding_authorized": True,
    "nfs_directory_creation_authorized": True,
    "nfs_record_copy_authorized": True,
    "systemd_unit_installation_authorized": True,
    "daemon_reload_authorized": True,
    "mount_enable_start_authorized": True,
    "authorization_consumption_authorized": True,
    "receipt_creation_authorized": True,
    "rollback_authorized": True,
    "parent_collective_change_authorized": False,
    "docker_restart_authorized": False,
    "k21d_installation_authorized": False,
    "k21d_activation_authorized": False,
}

AUTHORIZATION_GOVERNANCE = {
    "spot_core_sole_authority": True,
    "worker_self_apply_allowed": False,
    "live_executor_enabled": False,
    "execution_allowed": False,
    "mutation_authority": False,
}

TRANSACTION_GOVERNANCE = {
    "spot_core_sole_executor": True,
    "worker_self_apply_allowed": False,
    "parent_collective_change_allowed": False,
    "docker_restart_allowed": False,
    "k21d_installation_allowed": False,
    "k21d_activation_allowed": False,
    "execution_allowed": False,
    "mutation_authority": False,
}


class TransactionError(ValueError):
    """A deterministic transaction validation denial."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise TransactionError(message)


def exact(value: Any, keys: set[str], label: str) -> dict[str, Any]:
    require(isinstance(value, dict), f"{label} must be an object")
    require(set(value) == keys, f"{label} fields mismatch")
    return value


def parse_time(value: Any, label: str) -> datetime:
    require(isinstance(value, str), f"{label} must be a string")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise TransactionError(f"{label} is not ISO-8601") from exc
    require(parsed.tzinfo is not None, f"{label} lacks timezone")
    return parsed.astimezone(timezone.utc)


def regular(path: Path, label: str) -> None:
    try:
        info = path.lstat()
    except OSError as exc:
        raise TransactionError(f"{label} missing: {path}") from exc
    require(stat.S_ISREG(info.st_mode), f"{label} is not regular: {path}")


def digest(path: Path, label: str = "file") -> str:
    regular(path, label)
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def load_json(path: Path, label: str) -> dict[str, Any]:
    regular(path, label)
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise TransactionError(f"invalid {label}: {path}") from exc
    require(isinstance(value, dict), f"{label} must be an object")
    return value


def repo_path(repository: Path, value: Any, label: str) -> Path:
    require(isinstance(value, str) and value, f"{label} must be a path")
    require(not value.startswith("/"), f"{label} must be repository-relative")
    candidate = repository / value
    require(candidate.resolve() == candidate, f"{label} traverses a symlink")
    return candidate


def validate_review_result(path: Path, expected_id: str, expected_sha: str) -> None:
    require(digest(path, "review result") == expected_sha, "review digest mismatch")
    result = load_json(path, "review result")
    require(
        set(result)
        == {
            "review_id",
            "verdict",
            "execution_allowed",
            "confidence",
            "intent_match",
            "code_match",
            "policy_match",
            "backup_required",
            "backup_verified",
            "rollback_defined",
            "validation_defined",
            "required_fixes",
            "notes",
        },
        "review result fields mismatch",
    )
    require(result.get("review_id") == expected_id, "review ID mismatch")
    require(result.get("verdict") == "PASS", "review verdict is not PASS")
    require(result.get("execution_allowed") is False, "review grants execution")
    require(result.get("confidence") == "high", "review confidence is not high")
    require(result.get("intent_match") == "pass", "review intent mismatch")
    require(result.get("code_match") == "pass", "review code mismatch")
    require(result.get("policy_match") == "pass", "review policy mismatch")
    require(result.get("backup_required") is True, "review omits backup requirement")
    require(result.get("backup_verified") is True, "review omits backup verification")
    require(result.get("rollback_defined") is True, "review omits rollback")
    require(result.get("validation_defined") is True, "review omits validation")
    require(result.get("required_fixes") == [], "review has required fixes")
    require(
        isinstance(result.get("notes"), str) and bool(result["notes"]),
        "review notes missing",
    )


def validate_no_revocation(
    repository: Path,
    authorization_path: str,
    authorization_id: str,
    authorization_sha256: str,
) -> None:
    """Deny a transaction if any matching storage revocation names its authority."""

    review_directory = repository / "watch/review/bundles"
    require(review_directory.is_dir(), "review bundle directory missing")
    for revocation_path in sorted(
        review_directory.glob("REVOKE-STORAGE-POST239-K21D-*.json")
    ):
        revocation = load_json(revocation_path, "storage authorization revocation")
        if (
            revocation.get("revoked_authorization_path") == authorization_path
            or revocation.get("revoked_authorization_id") == authorization_id
            or revocation.get("revoked_authorization_sha256")
            == authorization_sha256
        ):
            raise TransactionError(
                f"storage authorization revoked: {revocation_path.name}"
            )


def validate_authorization(
    payload: dict[str, Any],
    transaction: dict[str, Any],
    *,
    now: datetime | None = None,
) -> None:
    top = exact(
        payload,
        {
            "schema",
            "authorization_id",
            "transaction_id",
            "generated_at",
            "expires_at",
            "authorized_by",
            "repository",
            "review",
            "scope",
            "replay_control",
            "governance",
            "status",
        },
        "authorization",
    )
    require(top["schema"] == AUTHORIZATION_SCHEMA, "wrong authorization schema")
    require(
        isinstance(top["authorization_id"], str)
        and AUTHORIZATION_ID.fullmatch(top["authorization_id"]) is not None,
        "bad authorization ID",
    )
    require(
        top["authorization_id"]
        == transaction["operator_authorization"]["authorization_id"],
        "authorization ID mismatch",
    )
    require(top["transaction_id"] == transaction["transaction_id"], "authorization transaction mismatch")
    generated = parse_time(top["generated_at"], "authorization generated_at")
    expires = parse_time(top["expires_at"], "authorization expires_at")
    require(generated < expires, "authorization is not forward-expiring")
    if now is not None:
        current = now.astimezone(timezone.utc)
        require(generated <= current < expires, "authorization expired or not yet valid")
    require(
        parse_time(transaction["expires_at"], "transaction expires_at") <= expires,
        "transaction outlives authorization",
    )

    authorized_by = exact(
        top["authorized_by"], {"role", "identity", "authority"}, "authorized_by"
    )
    require(authorized_by["role"] == "operator", "authorization role mismatch")
    require(isinstance(authorized_by["identity"], str) and authorized_by["identity"], "authorization identity missing")
    require(
        authorized_by["authority"] == "single_use_scoped_nfs_storage_only",
        "authorization authority mismatch",
    )

    repository = exact(
        top["repository"],
        {"host", "branch", "head", "required_clean_except_runtime_drift"},
        "authorization repository",
    )
    require(repository["host"] == "spot-core", "authorization host mismatch")
    require(repository["branch"] == "main", "authorization branch mismatch")
    require(repository["head"] == transaction["repository_head"], "authorization head mismatch")
    require(
        repository["required_clean_except_runtime_drift"] == RUNTIME_DRIFT,
        "authorization drift boundary mismatch",
    )

    review = exact(
        top["review"], {"review_id", "result_path", "result_sha256", "verdict"}, "authorization review"
    )
    implementation_review = transaction["implementation_review"]
    require(review["review_id"] == implementation_review["review_id"], "authorization review ID mismatch")
    require(review["result_path"] == implementation_review["result_path"], "authorization review path mismatch")
    require(review["result_sha256"] == implementation_review["result_sha256"], "authorization review digest mismatch")
    require(review["verdict"] == "PASS", "authorization review is not PASS")
    require(top["scope"] == AUTHORIZATION_SCOPE, "authorization scope mismatch")

    replay = exact(
        top["replay_control"],
        {"single_use", "consumed", "completed", "rollback_completed"},
        "replay control",
    )
    require(replay == {"single_use": True, "consumed": False, "completed": False, "rollback_completed": False}, "authorization replay state invalid")
    require(top["governance"] == AUTHORIZATION_GOVERNANCE, "authorization governance mismatch")
    require(top["status"] == AUTHORIZATION_STATUS, "authorization status invalid")


def validate_transaction(
    payload: dict[str, Any],
    repository: Path,
    *,
    reference_checks: bool = True,
    now: datetime | None = None,
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
            "implementation_review",
            "implementation",
            "operator_authorization",
            "backup",
            "rollback",
            "mounts",
            "preserved_objects",
            "governance",
            "status",
        },
        "transaction",
    )
    require(top["schema"] == TRANSACTION_SCHEMA, "wrong transaction schema")
    require(
        isinstance(top["transaction_id"], str)
        and TRANSACTION_ID.fullmatch(top["transaction_id"]) is not None,
        "bad transaction ID",
    )
    generated = parse_time(top["generated_at"], "generated_at")
    expires = parse_time(top["expires_at"], "expires_at")
    require(generated < expires, "transaction is not forward-expiring")
    if now is not None:
        current = now.astimezone(timezone.utc)
        require(generated <= current < expires, "transaction expired or not yet valid")
    require(top["host"] == "spot-core", "wrong transaction host")
    require(
        isinstance(top["repository_head"], str)
        and HEAD.fullmatch(top["repository_head"]) is not None,
        "bad repository head",
    )
    require(top["design_review"] == DESIGN_REVIEW, "design review binding mismatch")

    implementation_review = exact(
        top["implementation_review"],
        {
            "bundle_path",
            "bundle_sha256",
            "result_path",
            "result_sha256",
            "review_id",
            "reviewer",
            "model",
            "verdict",
        },
        "implementation review",
    )
    for field in ("bundle_sha256", "result_sha256"):
        require(isinstance(implementation_review[field], str) and SHA.fullmatch(implementation_review[field]) is not None, f"bad implementation review {field}")
    require(isinstance(implementation_review["review_id"], str) and implementation_review["review_id"], "implementation review ID missing")
    require(
        IMPLEMENTATION_REVIEW_ID.fullmatch(implementation_review["review_id"])
        is not None,
        "implementation review ID invalid",
    )
    require(
        implementation_review["bundle_path"]
        == f"watch/review/bundles/{implementation_review['review_id']}.md",
        "implementation review bundle path mismatch",
    )
    require(
        implementation_review["result_path"]
        == (
            f"watch/review/bundles/{implementation_review['review_id']}"
            ".worker05.json"
        ),
        "implementation review result path mismatch",
    )
    require(implementation_review["reviewer"] == "spot-worker-05", "wrong implementation reviewer")
    require(implementation_review["model"] == "deepseek-r1:32b", "wrong implementation review model")
    require(implementation_review["verdict"] == "PASS", "implementation review is not PASS")

    implementation = top["implementation"]
    require(isinstance(implementation, list) and len(implementation) == len(IMPLEMENTATION_PATHS), "implementation file count mismatch")
    implementation_by_path: dict[str, str] = {}
    for index, entry in enumerate(implementation, start=1):
        item = exact(entry, {"path", "sha256"}, f"implementation file {index}")
        require(isinstance(item["path"], str), f"implementation path invalid at {index}")
        require(isinstance(item["sha256"], str) and SHA.fullmatch(item["sha256"]) is not None, f"implementation digest invalid at {index}")
        require(item["path"] not in implementation_by_path, "duplicate implementation path")
        implementation_by_path[item["path"]] = item["sha256"]
    require(set(implementation_by_path) == set(IMPLEMENTATION_PATHS), "implementation path set mismatch")

    operator = exact(
        top["operator_authorization"],
        {"authorization_id", "record_path", "record_sha256", "single_use", "consumed"},
        "operator authorization",
    )
    require(isinstance(operator["authorization_id"], str) and AUTHORIZATION_ID.fullmatch(operator["authorization_id"]) is not None, "bad operator authorization ID")
    require(operator["record_path"] == f"watch/review/bundles/{operator['authorization_id']}.json", "authorization path mismatch")
    require(isinstance(operator["record_sha256"], str) and SHA.fullmatch(operator["record_sha256"]) is not None, "bad authorization digest")
    require(operator["single_use"] is True and operator["consumed"] is False, "authorization is not unused single-use")

    identity_suffix = top["transaction_id"].removeprefix("STORAGE-POST239-K21D-")
    require(
        operator["authorization_id"]
        == f"AUTH-STORAGE-POST239-K21D-{identity_suffix}",
        "authorization ID is not transaction-bound",
    )

    backup = exact(
        top["backup"],
        {"backup_id", "root", "binding_id", "create_before_mutation", "verified_before_mutation"},
        "backup",
    )
    require(isinstance(backup["backup_id"], str) and BACKUP_ID.fullmatch(backup["backup_id"]) is not None, "bad backup ID")
    require(backup["root"] == "/mnt/collective/backups/spot-core/post239-k21d-storage", "wrong backup root")
    require(isinstance(backup["binding_id"], str) and BACKUP_BINDING_ID.fullmatch(backup["binding_id"]) is not None, "bad backup binding ID")
    require(backup["create_before_mutation"] is True, "backup is not pre-mutation")
    require(backup["verified_before_mutation"] is True, "backup verification not required")
    require(
        backup["backup_id"] == f"BACKUP-STORAGE-POST239-K21D-{identity_suffix}",
        "backup ID is not transaction-bound",
    )
    require(
        backup["binding_id"]
        == f"BACKUP-BINDING-STORAGE-POST239-K21D-{identity_suffix}",
        "backup binding ID is not transaction-bound",
    )

    rollback = exact(
        top["rollback"],
        {"document_path", "document_sha256", "binding_id", "verified"},
        "rollback",
    )
    require(rollback["document_path"] == "watch/storage/post239-k21d-scoped-nfs-storage-rollback.md", "wrong rollback document")
    require(isinstance(rollback["document_sha256"], str) and SHA.fullmatch(rollback["document_sha256"]) is not None, "bad rollback digest")
    require(isinstance(rollback["binding_id"], str) and ROLLBACK_BINDING_ID.fullmatch(rollback["binding_id"]) is not None, "bad rollback binding ID")
    require(rollback["verified"] is True, "rollback not verified")
    require(
        rollback["binding_id"]
        == f"ROLLBACK-BINDING-STORAGE-POST239-K21D-{identity_suffix}",
        "rollback binding ID is not transaction-bound",
    )

    mounts = top["mounts"]
    require(isinstance(mounts, list) and len(mounts) == 2, "mount count mismatch")
    for index, (item_value, expected) in enumerate(zip(mounts, MOUNTS), start=1):
        item = exact(
            item_value,
            {
                "purpose",
                "source",
                "target",
                "unit_name",
                "template_path",
                "template_sha256",
                "installed_path",
                "active_before",
                "enabled_before",
            },
            f"mount {index}",
        )
        for field, expected_value in expected.items():
            require(item[field] == expected_value, f"mount {index} {field} mismatch")
        require(isinstance(item["template_sha256"], str) and SHA.fullmatch(item["template_sha256"]) is not None, f"mount {index} template digest invalid")
        require(item["active_before"] is False and item["enabled_before"] is False, f"mount {index} pre-state unsafe")
        require(implementation_by_path[item["template_path"]] == item["template_sha256"], f"mount {index} template binding mismatch")

    require(top["preserved_objects"] == list(PRESERVED_OBJECTS), "preserved object set mismatch")
    require(top["governance"] == TRANSACTION_GOVERNANCE, "transaction governance mismatch")
    require(top["status"] == TRANSACTION_STATUS, "transaction status invalid")

    if not reference_checks:
        return

    for path_text, expected_sha, label in (
        (DESIGN_REVIEW["design_path"], DESIGN_REVIEW["design_sha256"], "design"),
        (DESIGN_REVIEW["contract_path"], DESIGN_REVIEW["contract_sha256"], "design contract"),
        (DESIGN_REVIEW["bundle_path"], DESIGN_REVIEW["bundle_sha256"], "design review bundle"),
        (DESIGN_REVIEW["result_path"], DESIGN_REVIEW["result_sha256"], "design review result"),
        (implementation_review["bundle_path"], implementation_review["bundle_sha256"], "implementation review bundle"),
        (implementation_review["result_path"], implementation_review["result_sha256"], "implementation review result"),
        (rollback["document_path"], rollback["document_sha256"], "rollback document"),
    ):
        path = repo_path(repository, path_text, label)
        require(digest(path, label) == expected_sha, f"{label} digest mismatch")

    validate_review_result(
        repo_path(repository, DESIGN_REVIEW["result_path"], "design review result"),
        DESIGN_REVIEW["review_id"],
        DESIGN_REVIEW["result_sha256"],
    )
    validate_review_result(
        repo_path(repository, implementation_review["result_path"], "implementation review result"),
        implementation_review["review_id"],
        implementation_review["result_sha256"],
    )

    for path_text, expected_sha in implementation_by_path.items():
        path = repo_path(repository, path_text, "implementation file")
        require(digest(path, "implementation file") == expected_sha, f"implementation digest mismatch: {path_text}")

    authorization_path = repo_path(repository, operator["record_path"], "authorization")
    require(digest(authorization_path, "authorization") == operator["record_sha256"], "authorization digest mismatch")
    authorization = load_json(authorization_path, "authorization")
    validate_authorization(authorization, top, now=now)
    validate_no_revocation(
        repository,
        operator["record_path"],
        operator["authorization_id"],
        operator["record_sha256"],
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate one K21D scoped NFS storage transaction")
    parser.add_argument("--transaction", type=Path, required=True)
    parser.add_argument("--repository", type=Path, default=Path.cwd())
    parser.add_argument("--offline-no-reference-check", action="store_true")
    args = parser.parse_args()

    transaction = load_json(args.transaction, "transaction")
    validate_transaction(
        transaction,
        args.repository,
        reference_checks=not args.offline_no_reference_check,
        now=None if args.offline_no_reference_check else datetime.now(timezone.utc),
    )
    print("[PASS] K21D scoped NFS storage transaction validated")
    print(f"transaction_id={transaction['transaction_id']}")
    print("storage_mutation_performed=false")
    print("daemon_reload_performed=false")
    print("docker_restarted=false")
    print("k21d_installation_performed=false")
    print("execution_allowed=false")
    print("mutation_authority=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
