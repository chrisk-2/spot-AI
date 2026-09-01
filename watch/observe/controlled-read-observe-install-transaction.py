#!/usr/bin/env python3
"""Fail-closed K21D installation-only transaction executor.

The live CLI is restricted to spot-core, the fixed repository, the reviewed
eight-file mapping, and one transaction/authorization/backup identity.  It
never starts, enables, schedules, or invokes the observer.
"""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import importlib.util
import json
import os
import socket
import stat
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Sequence


FILE_MAP = [
    (
        "watch/observe/controlled-read-observe.py",
        "/usr/local/lib/spot/observe/controlled-read-observe.py",
        "0755",
    ),
    (
        "watch/observe/controlled_read_observe_validation_v1.py",
        "/usr/local/lib/spot/observe/controlled_read_observe_validation_v1.py",
        "0755",
    ),
    (
        "watch/observe/controlled-read-observe-request-validate.py",
        "/usr/local/lib/spot/observe/controlled-read-observe-request-validate.py",
        "0755",
    ),
    (
        "watch/observe/controlled-read-observe-evidence-validate.py",
        "/usr/local/lib/spot/observe/controlled-read-observe-evidence-validate.py",
        "0755",
    ),
    (
        "watch/observe/controlled-read-observe-allowlist-v1.json",
        "/etc/spot/observe/controlled-read-observe-allowlist-v1.json",
        "0644",
    ),
    (
        "watch/observe/controlled-read-observe-request-schema-v1.json",
        "/etc/spot/observe/controlled-read-observe-request-schema-v1.json",
        "0644",
    ),
    (
        "watch/observe/controlled-read-observe-evidence-schema-v1.json",
        "/etc/spot/observe/controlled-read-observe-evidence-schema-v1.json",
        "0644",
    ),
    (
        "watch/observe/controlled-read-observe.service",
        "/etc/systemd/system/spot-controlled-read-observe.service",
        "0644",
    ),
]

LIVE_REPOSITORY = Path("/home/ogre/spot-stack")
BACKUP_BASE = Path("/mnt/collective/backups/spot-core/post239-k21d")
EVIDENCE_BASE = Path("/mnt/collective/logs/spot/actions/post239-k21d")
LOCK_PATH = Path("/run/lock/spot-post239-k21d-install.lock")
RUNTIME_REQUEST = Path("/var/lib/spot/controlled-read-observe/request.json")
RUNTIME_EVIDENCE = Path("/var/lib/spot/controlled-read-observe/evidence")
RUNTIME_DRIFT = "starfleet-ui/public/status.json"
SERVICE = "spot-controlled-read-observe.service"
TRANSACTION_VALIDATOR = Path(
    "watch/observe/controlled-read-observe-install-transaction-validate.py"
)
BACKUP_SCHEMA = "starfleet.post239.k21d_install_backup.v1"
AUTH_SCHEMA = "starfleet.post239.k21d_installation_authorization.v1"
RECEIPT_SCHEMA = "starfleet.post239.k21d_installation_receipt.v1"
CONSUMPTION_SCHEMA = "starfleet.post239.k21d_authorization_consumption.v1"
MAX_JSON_BYTES = 2 * 1024 * 1024


class ExecutionError(RuntimeError):
    """A fail-closed installation denial or transaction failure."""


@dataclass
class CommandResult:
    returncode: int
    stdout: str = ""
    stderr: str = ""


CommandRunner = Callable[[Sequence[str], Path | None], CommandResult]


@dataclass
class ExecutionContext:
    repository: Path
    system_root: Path
    lock_path: Path
    command_runner: CommandRunner
    now: Callable[[], datetime]
    hostname: Callable[[], str]
    live: bool

    def absolute(self, value: str | Path) -> Path:
        path = Path(value)
        require(path.is_absolute(), f"path is not absolute: {path}")
        if self.system_root == Path("/"):
            return path
        return self.system_root / str(path).lstrip("/")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ExecutionError(message)


def exact_keys(value: Any, keys: set[str], label: str) -> dict[str, Any]:
    require(isinstance(value, dict), f"{label} must be an object")
    require(set(value) == keys, f"{label} fields mismatch: {sorted(set(value) ^ keys)}")
    return value


def utc_text(value: datetime | None = None) -> str:
    current = value or datetime.now(timezone.utc)
    return current.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def parse_time(value: Any, label: str) -> datetime:
    require(isinstance(value, str), f"{label} must be a string")
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ExecutionError(f"invalid {label}") from exc
    require(result.tzinfo is not None, f"{label} lacks timezone")
    return result.astimezone(timezone.utc)


def regular_lstat(path: Path, label: str) -> os.stat_result:
    try:
        info = path.lstat()
    except FileNotFoundError as exc:
        raise ExecutionError(f"{label} missing: {path}") from exc
    require(stat.S_ISREG(info.st_mode), f"{label} is not a regular file: {path}")
    require(not path.is_symlink(), f"{label} is a symlink: {path}")
    return info


def digest_file(path: Path, label: str = "file") -> str:
    regular_lstat(path, label)
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags)
    value = hashlib.sha256()
    try:
        opened = os.fstat(descriptor)
        require(stat.S_ISREG(opened.st_mode), f"{label} changed type: {path}")
        with os.fdopen(descriptor, "rb", closefd=False) as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                value.update(chunk)
    finally:
        os.close(descriptor)
    return value.hexdigest()


def read_regular_bytes(
    path: Path,
    label: str,
    *,
    maximum: int | None = None,
) -> bytes:
    regular_lstat(path, label)
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags)
    try:
        opened = os.fstat(descriptor)
        require(stat.S_ISREG(opened.st_mode), f"{label} changed type: {path}")
        if maximum is not None:
            require(opened.st_size <= maximum, f"{label} exceeds size limit")
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            total += len(chunk)
            if maximum is not None:
                require(total <= maximum, f"{label} exceeds size limit")
            chunks.append(chunk)
        closed = os.fstat(descriptor)
        require(
            (opened.st_dev, opened.st_ino, opened.st_size)
            == (closed.st_dev, closed.st_ino, closed.st_size),
            f"{label} changed while reading: {path}",
        )
        return b"".join(chunks)
    finally:
        os.close(descriptor)


def read_json(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(
            read_regular_bytes(path, label, maximum=MAX_JSON_BYTES).decode("utf-8")
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ExecutionError(f"cannot parse {label}: {exc}") from exc
    require(isinstance(payload, dict), f"{label} must be an object")
    return payload


def fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def atomic_json_exclusive(path: Path, payload: dict[str, Any]) -> None:
    require(path.is_absolute(), "journal path must be absolute")
    require(path.parent.is_dir(), f"journal directory missing: {path.parent}")
    require(not os.path.lexists(path), f"journal already exists: {path}")
    data = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode()
    descriptor, temporary_text = tempfile.mkstemp(
        prefix=f".{path.name}.", dir=path.parent
    )
    temporary = Path(temporary_text)
    linked = False
    try:
        os.fchmod(descriptor, 0o600)
        os.write(descriptor, data)
        os.fsync(descriptor)
        os.close(descriptor)
        descriptor = -1
        os.link(temporary, path, follow_symlinks=False)
        linked = True
        fsync_directory(path.parent)
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
        if not linked and os.path.lexists(path):
            raise ExecutionError(f"exclusive journal collision: {path}")


def default_runner(arguments: Sequence[str], cwd: Path | None) -> CommandResult:
    completed = subprocess.run(
        list(arguments),
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=120,
    )
    return CommandResult(completed.returncode, completed.stdout, completed.stderr)


def run_checked(
    context: ExecutionContext,
    arguments: Sequence[str],
    label: str,
    *,
    cwd: Path | None = None,
) -> CommandResult:
    result = context.command_runner(arguments, cwd)
    require(
        result.returncode == 0,
        f"{label} failed: {(result.stderr or result.stdout).strip()}",
    )
    return result


def load_transaction_validator(repository: Path) -> Any:
    path = repository / TRANSACTION_VALIDATOR
    regular_lstat(path, "transaction validator")
    spec = importlib.util.spec_from_file_location("k21d_transaction_validator", path)
    require(spec is not None and spec.loader is not None, "cannot load validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate_repository(context: ExecutionContext, head: str) -> None:
    if not context.live:
        return
    require(context.repository.resolve() == LIVE_REPOSITORY, "wrong repository")
    require(context.hostname() == "spot-core", "wrong execution host")
    require(os.geteuid() == 0, "live installation requires root")
    checks = (
        (["git", "branch", "--show-current"], "main", "wrong branch"),
        (["git", "rev-parse", "HEAD"], head, "repository head mismatch"),
        (["git", "rev-parse", "origin/main"], head, "origin/main mismatch"),
    )
    for command, expected, label in checks:
        result = run_checked(context, command, label, cwd=context.repository)
        require(result.stdout.strip() == expected, label)
    staged = run_checked(
        context,
        ["git", "diff", "--cached", "--name-only"],
        "staged-diff check",
        cwd=context.repository,
    )
    require(not staged.stdout.strip(), "staged changes present")
    drift = run_checked(
        context,
        ["git", "diff", "--name-only"],
        "worktree check",
        cwd=context.repository,
    )
    require(drift.stdout.strip() == RUNTIME_DRIFT, "unexpected worktree drift")


def expected_mapping(transaction: dict[str, Any]) -> list[dict[str, Any]]:
    files = transaction.get("files")
    require(isinstance(files, list) and len(files) == 8, "wrong file count")
    result: list[dict[str, Any]] = []
    for index, ((source, destination, mode), item) in enumerate(
        zip(FILE_MAP, files), start=1
    ):
        require(isinstance(item, dict), f"file {index} is not an object")
        require(item.get("source") == source, f"file {index} source mismatch")
        require(
            item.get("destination") == destination,
            f"file {index} destination mismatch",
        )
        require(item.get("mode") == mode, f"file {index} mode mismatch")
        result.append(
            {
                "source": source,
                "source_sha256": item.get("source_sha256"),
                "destination": destination,
                "mode": mode,
                "owner": "root",
                "group": "root",
            }
        )
    return result


def validate_authorization(
    context: ExecutionContext,
    transaction: dict[str, Any],
    authorization_path: Path,
    authorization_sha256: str,
) -> dict[str, Any]:
    authorization = read_json(authorization_path, "installation authorization")
    require(digest_file(authorization_path) == authorization_sha256, "authorization digest mismatch")
    exact_keys(
        authorization,
        {
            "schema",
            "authorization_id",
            "generated_at",
            "expires_at",
            "authorized_by",
            "repository",
            "correlated_reviews",
            "fixed_mappings",
            "scope",
            "replay_control",
            "governance",
            "status",
        },
        "installation authorization",
    )
    operator = transaction["operator_authorization"]
    require(authorization.get("schema") == AUTH_SCHEMA, "wrong authorization schema")
    require(
        authorization.get("authorization_id") == operator["authorization_id"],
        "authorization ID mismatch",
    )
    require(authorization.get("status") == "AUTHORIZED_FOR_SINGLE_K21D_INSTALLATION_ONLY", "authorization status invalid")

    generated = parse_time(authorization.get("generated_at"), "authorization generated_at")
    expires = parse_time(authorization.get("expires_at"), "authorization expires_at")
    now = context.now().astimezone(timezone.utc)
    require(generated < expires, "authorization is not forward-expiring")
    require(generated <= now < expires, "authorization expired or not yet valid")
    require(parse_time(transaction["expires_at"], "transaction expires_at") <= expires, "transaction outlives authorization")

    authorized_by = exact_keys(
        authorization.get("authorized_by"),
        {"role", "identity", "authority"},
        "authorized_by",
    )
    require(authorized_by["role"] == "operator", "authorization role mismatch")
    require(isinstance(authorized_by["identity"], str) and authorized_by["identity"], "authorization identity missing")
    require(authorized_by["authority"] == "single_use_installation_only", "authorization authority mismatch")

    repository = exact_keys(
        authorization.get("repository"),
        {"host", "branch", "head", "required_clean_except_runtime_drift"},
        "authorization repository",
    )
    require(repository.get("host") == "spot-core", "authorization host mismatch")
    require(repository.get("branch") == "main", "authorization branch mismatch")
    require(repository.get("head") == transaction["repository_head"], "authorization head mismatch")
    require(repository.get("required_clean_except_runtime_drift") == RUNTIME_DRIFT, "authorization drift boundary mismatch")

    reviews = exact_keys(
        authorization.get("correlated_reviews"),
        {
            "blueprint_pass_path",
            "blueprint_pass_sha256",
            "implementation_pass_path",
            "implementation_pass_sha256",
            "mapping_correction_pass_path",
            "mapping_correction_pass_sha256",
            "live_executor_pass_path",
            "live_executor_pass_sha256",
            "worker05_verdict",
        },
        "correlated reviews",
    )
    require(reviews["worker05_verdict"] == "PASS", "Worker-05 review not PASS")
    for prefix in (
        "blueprint_pass",
        "implementation_pass",
        "mapping_correction_pass",
        "live_executor_pass",
    ):
        relative = reviews[f"{prefix}_path"]
        expected_digest = reviews[f"{prefix}_sha256"]
        require(isinstance(relative, str) and relative.startswith("watch/review/bundles/"), f"bad {prefix} path")
        review_path = (context.repository / relative).resolve()
        require(context.repository in review_path.parents, f"{prefix} path escapes repository")
        require(digest_file(review_path, prefix) == expected_digest, f"{prefix} digest mismatch")
    live_review = read_json(
        (context.repository / reviews["live_executor_pass_path"]).resolve(),
        "live executor PASS",
    )
    require(live_review.get("verdict") == "PASS", "live executor verdict not PASS")
    require(live_review.get("live_executor_accepted") is True, "live executor not accepted")
    require(live_review.get("system_path_installation_authorized") is False, "review record improperly authorizes installation")

    mappings = authorization.get("fixed_mappings")
    require(mappings == expected_mapping(transaction), "authorization mapping mismatch")

    scope = exact_keys(
        authorization.get("scope"),
        {
            "k21d_transaction_authorized",
            "backup_creation_authorized",
            "installation_manifest_creation_authorized",
            "system_path_installation_authorized",
            "installation_receipt_creation_authorized",
            "authorization_consumption_authorized",
            "daemon_reload_if_unit_changed_authorized",
            "rollback_execution_authorized",
            "rollback_stop_if_unexpected_active_authorized",
            "unconditional_daemon_reload_authorized",
            "activation_authorized",
            "enablement_authorized",
            "scheduling_authorized",
            "request_dispatch_authorized",
            "production_observation_authorized",
            "service_action_authorized",
            "remediation_authorized",
        },
        "authorization scope",
    )
    for field in (
        "k21d_transaction_authorized",
        "backup_creation_authorized",
        "installation_manifest_creation_authorized",
        "system_path_installation_authorized",
        "installation_receipt_creation_authorized",
        "authorization_consumption_authorized",
        "daemon_reload_if_unit_changed_authorized",
        "rollback_execution_authorized",
        "rollback_stop_if_unexpected_active_authorized",
    ):
        require(scope.get(field) is True, f"required authority absent: {field}")
    for field in (
        "unconditional_daemon_reload_authorized",
        "activation_authorized",
        "enablement_authorized",
        "scheduling_authorized",
        "request_dispatch_authorized",
        "production_observation_authorized",
        "service_action_authorized",
        "remediation_authorized",
    ):
        require(scope.get(field) is False, f"unsafe authority present: {field}")

    replay = exact_keys(
        authorization.get("replay_control"),
        {"single_use", "consumed", "installation_completed", "rollback_completed"},
        "replay control",
    )
    require(replay.get("single_use") is True, "authorization is not single-use")
    require(replay.get("consumed") is False, "authorization already consumed")
    require(replay.get("installation_completed") is False, "authorization already completed")

    governance = exact_keys(
        authorization.get("governance"),
        {
            "spot_core_sole_authority",
            "worker_self_apply_allowed",
            "live_executor_enabled",
            "execution_allowed",
            "mutation_authority",
        },
        "authorization governance",
    )
    require(governance.get("spot_core_sole_authority") is True, "Spot Core authority missing")
    for field in (
        "worker_self_apply_allowed",
        "live_executor_enabled",
        "execution_allowed",
        "mutation_authority",
    ):
        require(governance.get(field) is False, f"unsafe governance state: {field}")

    review_dir = context.repository / "watch/review/bundles"
    for revocation_path in review_dir.glob("REVOKE-POST239-K21D-INSTALLATION-*.json"):
        revocation = read_json(revocation_path, "authorization revocation")
        if (
            revocation.get("revoked_authorization_path")
            == operator["record_path"]
            or revocation.get("revoked_authorization_sha256")
            == authorization_sha256
        ):
            raise ExecutionError(f"authorization revoked: {revocation_path.name}")
    return authorization


def validate_backup(
    context: ExecutionContext,
    transaction: dict[str, Any],
    authorization: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    backup = transaction["backup"]
    expected_manifest = BACKUP_BASE / f"{backup['manifest_id']}.json"
    require(Path(backup["manifest_path"]) == expected_manifest, "backup manifest path mismatch")
    physical_manifest = context.absolute(expected_manifest)
    require(physical_manifest.resolve() == physical_manifest, "backup manifest path traverses a symlink")
    manifest = read_json(physical_manifest, "backup manifest")
    exact_keys(
        manifest,
        {
            "schema",
            "manifest_id",
            "generated_at",
            "host",
            "repository_head",
            "authorization_id",
            "authorization_sha256",
            "binding_id",
            "files",
            "verified",
            "status",
        },
        "backup manifest",
    )
    require(digest_file(physical_manifest) == backup["manifest_sha256"], "backup manifest digest mismatch")
    require(manifest.get("schema") == BACKUP_SCHEMA, "wrong backup schema")
    require(manifest.get("manifest_id") == backup["manifest_id"], "backup ID mismatch")
    require(manifest.get("binding_id") == backup["binding_id"], "backup binding mismatch")
    require(manifest.get("host") == "spot-core", "backup host mismatch")
    require(manifest.get("repository_head") == transaction["repository_head"], "backup repository mismatch")
    require(manifest.get("authorization_id") == authorization["authorization_id"], "backup authorization mismatch")
    require(manifest.get("authorization_sha256") == transaction["operator_authorization"]["record_sha256"], "backup authorization digest mismatch")
    require(manifest.get("verified") is True, "backup is not verified")
    require(manifest.get("status") == "VERIFIED_PREINSTALL_BACKUP", "backup status invalid")
    entries = manifest.get("files")
    require(isinstance(entries, list) and len(entries) == 8, "backup file count mismatch")

    verified: list[dict[str, Any]] = []
    backup_dir = BACKUP_BASE / f"{backup['manifest_id']}-files"
    for index, (entry, transaction_file, mapping) in enumerate(
        zip(entries, transaction["files"], FILE_MAP), start=1
    ):
        source, destination, _mode = mapping
        exact_keys(
            entry,
            {
                "source",
                "destination",
                "destination_preexisting",
                "destination_type_before",
                "backup_path",
                "backup_sha256",
                "mode_before",
                "uid_before",
                "gid_before",
            },
            f"backup entry {index}",
        )
        require(entry.get("source") == source, f"backup source mismatch at {index}")
        require(entry.get("destination") == destination, f"backup destination mismatch at {index}")
        require(entry.get("destination_preexisting") is transaction_file["destination_preexisting"], f"backup state mismatch at {index}")
        require(entry.get("destination_type_before") == transaction_file["destination_type_before"], f"backup type mismatch at {index}")
        require(entry.get("backup_sha256") == transaction_file["backup_sha256"], f"backup digest binding mismatch at {index}")
        if transaction_file["destination_preexisting"]:
            expected_path = backup_dir / f"{index:02d}-{Path(destination).name}.backup"
            require(entry.get("backup_path") == str(expected_path), f"backup path mismatch at {index}")
            physical = context.absolute(expected_path)
            require(physical.resolve() == physical, f"backup path traverses a symlink at {index}")
            require(digest_file(physical, f"backup file {index}") == entry["backup_sha256"], f"backup content mismatch at {index}")
            require(
                isinstance(entry["mode_before"], str)
                and len(entry["mode_before"]) == 4
                and all(character in "01234567" for character in entry["mode_before"]),
                f"backup mode invalid at {index}",
            )
            require(isinstance(entry["uid_before"], int) and entry["uid_before"] >= 0, f"backup uid invalid at {index}")
            require(isinstance(entry["gid_before"], int) and entry["gid_before"] >= 0, f"backup gid invalid at {index}")
        else:
            require(entry.get("backup_path") is None, f"unexpected backup path at {index}")
            require(entry.get("backup_sha256") is None, f"unexpected backup digest at {index}")
            require(entry.get("mode_before") is None, f"unexpected backup mode at {index}")
            require(entry.get("uid_before") is None, f"unexpected backup uid at {index}")
            require(entry.get("gid_before") is None, f"unexpected backup gid at {index}")
        verified.append(entry)
    return manifest, verified


def destination_state(
    context: ExecutionContext,
    item: dict[str, Any],
    backup: dict[str, Any],
    index: int,
) -> None:
    destination = context.absolute(item["destination"])
    exists = os.path.lexists(destination)
    if item["destination_preexisting"]:
        require(exists, f"preexisting destination missing at {index}")
        info = regular_lstat(destination, f"destination {index}")
        require(digest_file(destination) == item["backup_sha256"], f"destination changed after backup at {index}")
        require(stat.S_IMODE(info.st_mode) == int(backup["mode_before"], 8), f"destination mode changed after backup at {index}")
        require(info.st_uid == backup["uid_before"], f"destination uid changed after backup at {index}")
        require(info.st_gid == backup["gid_before"], f"destination gid changed after backup at {index}")
    else:
        require(not exists, f"destination unexpectedly exists at {index}")


def secure_parent(context: ExecutionContext, destination: Path, created: list[Path]) -> None:
    allowed = {
        context.absolute("/usr/local/lib/spot/observe"),
        context.absolute("/etc/spot/observe"),
        context.absolute("/etc/systemd/system"),
    }
    parent = destination.parent
    require(parent in allowed, f"destination parent not allowed: {parent}")
    if not parent.exists():
        require(parent.parent.is_dir(), f"fixed parent base missing: {parent.parent}")
        require(parent.parent.resolve() == parent.parent, f"fixed parent base is unsafe: {parent.parent}")
        parent.mkdir(mode=0o755)
        if context.live:
            os.chown(parent, 0, 0)
        created.append(parent)
        fsync_directory(parent.parent)
    info = parent.lstat()
    require(stat.S_ISDIR(info.st_mode) and not parent.is_symlink(), f"unsafe destination parent: {parent}")
    require(parent.resolve() == parent, f"destination parent traverses symlink: {parent}")
    require(info.st_mode & 0o022 == 0, f"writable destination parent: {parent}")
    if context.live:
        require(info.st_uid == 0 and info.st_gid == 0, f"destination parent not root-owned: {parent}")


def atomic_install(
    context: ExecutionContext,
    source: Path,
    destination: Path,
    mode: str,
    created_directories: list[Path],
    expected_sha256: str,
    uid: int = 0,
    gid: int = 0,
) -> None:
    secure_parent(context, destination, created_directories)
    data = read_regular_bytes(source, "atomic installation source")
    require(hashlib.sha256(data).hexdigest() == expected_sha256, "atomic source digest mismatch")
    descriptor, temporary_text = tempfile.mkstemp(prefix=".spot-k21d-", dir=destination.parent)
    temporary = Path(temporary_text)
    try:
        os.fchmod(descriptor, int(mode, 8))
        if context.live:
            os.fchown(descriptor, uid, gid)
        os.write(descriptor, data)
        os.fsync(descriptor)
        os.close(descriptor)
        descriptor = -1
        os.replace(temporary, destination)
        fsync_directory(destination.parent)
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def verify_installed(context: ExecutionContext, transaction: dict[str, Any]) -> None:
    for index, item in enumerate(transaction["files"], start=1):
        destination = context.absolute(item["destination"])
        info = regular_lstat(destination, f"installed destination {index}")
        require(digest_file(destination) == item["source_sha256"], f"installed digest mismatch at {index}")
        require(stat.S_IMODE(info.st_mode) == int(item["mode"], 8), f"installed mode mismatch at {index}")
        if context.live:
            require(info.st_uid == 0 and info.st_gid == 0, f"installed ownership mismatch at {index}")


def snapshot_path(path: Path) -> str:
    value = hashlib.sha256()
    if not os.path.lexists(path):
        value.update(b"absent")
        return value.hexdigest()
    root_info = path.lstat()
    if stat.S_ISREG(root_info.st_mode):
        value.update(b"file\0" + digest_file(path).encode())
        return value.hexdigest()
    if stat.S_ISLNK(root_info.st_mode):
        value.update(b"link\0" + os.readlink(path).encode())
        return value.hexdigest()
    require(stat.S_ISDIR(root_info.st_mode), f"unsupported runtime path type: {path}")
    value.update(b"directory\0")
    for child in sorted(path.rglob("*"), key=lambda item: str(item.relative_to(path))):
        relative = str(child.relative_to(path)).encode()
        info = child.lstat()
        value.update(relative + b"\0" + oct(stat.S_IMODE(info.st_mode)).encode() + b"\0")
        if stat.S_ISREG(info.st_mode):
            value.update(digest_file(child).encode())
        elif stat.S_ISLNK(info.st_mode):
            value.update(b"link:" + os.readlink(child).encode())
        elif stat.S_ISDIR(info.st_mode):
            value.update(b"directory")
        else:
            value.update(f"special:{stat.S_IFMT(info.st_mode)}".encode())
    return value.hexdigest()


def running_services(context: ExecutionContext) -> str:
    result = run_checked(
        context,
        ["systemctl", "list-units", "--type=service", "--state=running", "--no-legend", "--no-pager", "--plain"],
        "running-service snapshot",
    )
    lines = [line for line in result.stdout.splitlines() if SERVICE not in line]
    return "\n".join(sorted(line.strip() for line in lines if line.strip()))


def assert_service_safe(context: ExecutionContext, *, unit_must_exist: bool) -> dict[str, Any]:
    active = context.command_runner(["systemctl", "is-active", SERVICE], None)
    active_state = active.stdout.strip()
    require(active_state in {"inactive", "unknown"}, f"observer is not inactive: {active_state}")
    if unit_must_exist:
        require(active_state == "inactive", "installed observer unit is not inactive")
    enabled = context.command_runner(["systemctl", "is-enabled", SERVICE], None)
    enabled_state = enabled.stdout.strip()
    safe_enabled = {"disabled", "static", "not-found", "unknown"}
    require(enabled_state in safe_enabled, f"observer is enabled: {enabled_state}")
    if unit_must_exist:
        require(enabled_state in {"disabled", "static"}, "installed observer unit enablement state unsafe")
    main_pid = context.command_runner(["systemctl", "show", SERVICE, "--property=MainPID", "--value"], None)
    require(main_pid.returncode in {0, 1, 3, 4}, "cannot inspect observer MainPID")
    require(main_pid.stdout.strip() in {"", "0"}, "observer process exists")
    timers = context.command_runner(
        ["systemctl", "list-unit-files", "spot-controlled-read-observe*.timer", "--no-legend", "--no-pager"],
        None,
    )
    require(timers.returncode == 0, "cannot inspect observer timers")
    require(not timers.stdout.strip(), "controlled-read-observe timer registered")
    for base in ("/etc/systemd/system", "/usr/lib/systemd/system", "/lib/systemd/system"):
        physical = context.absolute(base)
        if physical.is_dir():
            require(not list(physical.glob("*controlled-read-observe*.timer")), "controlled-read-observe timer file exists")
    return {"active_state": active_state, "enabled_state": enabled_state, "main_pid": main_pid.stdout.strip() or "0"}


def run_offline_regressions(context: ExecutionContext) -> list[str]:
    commands = (
        ["python3", "watch/observe/controlled_read_observe_validation_v1.py"],
        ["python3", "watch/observe/controlled-read-observe-replay-bounds-validate.py"],
        ["python3", "watch/observe/controlled-read-observe-install-validate.py"],
        ["python3", "watch/observe/controlled-read-observe-install-transaction-failure-test.py"],
    )
    passed: list[str] = []
    for command in commands:
        run_checked(context, command, f"offline regression {command[1]}", cwd=context.repository)
        passed.append(command[1])
    return passed


def rollback_installation(
    context: ExecutionContext,
    transaction: dict[str, Any],
    authorization: dict[str, Any],
    backup_entries: list[dict[str, Any]],
    installed_indices: list[int],
    created_directories: list[Path],
    unit_changed: bool,
) -> dict[str, Any]:
    failures: list[str] = []
    restored: list[str] = []
    active = context.command_runner(["systemctl", "is-active", SERVICE], None)
    if active.stdout.strip() == "active":
        try:
            require(
                authorization["scope"]["rollback_stop_if_unexpected_active_authorized"] is True,
                "rollback stop authority absent",
            )
            run_checked(
                context,
                ["systemctl", "stop", SERVICE],
                "rollback stop of unexpectedly active observer",
            )
        except ExecutionError as exc:
            failures.append(str(exc))
    installed_set = set(installed_indices)
    for index in reversed(range(1, len(transaction["files"]) + 1)):
        if index not in installed_set:
            continue
        item = transaction["files"][index - 1]
        backup = backup_entries[index - 1]
        destination = context.absolute(item["destination"])
        try:
            if item["destination_preexisting"]:
                backup_path = context.absolute(backup["backup_path"])
                require(digest_file(backup_path) == item["backup_sha256"], f"rollback backup mismatch at {index}")
                atomic_install(
                    context,
                    backup_path,
                    destination,
                    backup["mode_before"],
                    created_directories,
                    item["backup_sha256"],
                    backup["uid_before"],
                    backup["gid_before"],
                )
                require(digest_file(destination) == item["backup_sha256"], f"rollback restore mismatch at {index}")
            else:
                if os.path.lexists(destination):
                    regular_lstat(destination, f"rollback destination {index}")
                    require(digest_file(destination) == item["source_sha256"], f"rollback refuses changed destination at {index}")
                    destination.unlink()
                    fsync_directory(destination.parent)
                require(not os.path.lexists(destination), f"rollback removal failed at {index}")
            restored.append(item["destination"])
        except (OSError, ExecutionError) as exc:
            failures.append(str(exc))
    if unit_changed:
        try:
            run_checked(context, ["systemctl", "daemon-reload"], "rollback daemon-reload")
        except ExecutionError as exc:
            failures.append(str(exc))
    for directory in reversed(created_directories):
        try:
            directory.rmdir()
            fsync_directory(directory.parent)
        except OSError:
            pass
    try:
        assert_service_safe(context, unit_must_exist=False)
    except ExecutionError as exc:
        failures.append(str(exc))
    return {"restored": restored, "failures": failures, "succeeded": not failures}


def consumption_and_receipt_paths(context: ExecutionContext, transaction_id: str) -> tuple[Path, Path]:
    evidence = context.absolute(EVIDENCE_BASE)
    return (
        evidence / f"{transaction_id}.consumption.json",
        evidence / f"{transaction_id}.receipt.json",
    )


def execute_transaction(context: ExecutionContext, transaction_path: Path) -> dict[str, Any]:
    context.repository = context.repository.resolve()
    transaction = read_json(transaction_path, "installation transaction")
    validator = load_transaction_validator(context.repository)
    try:
        validator.validate_transaction(transaction, context.repository, verify_references=True)
    except Exception as exc:  # validator owns its exception type
        raise ExecutionError(f"transaction validation failed: {exc}") from exc

    require(transaction.get("host") == "spot-core", "transaction host mismatch")
    require(context.hostname() == "spot-core", "wrong execution host")
    now = context.now().astimezone(timezone.utc)
    require(parse_time(transaction["generated_at"], "transaction generated_at") <= now, "transaction not yet valid")
    require(now < parse_time(transaction["expires_at"], "transaction expires_at"), "transaction expired")
    validate_repository(context, transaction["repository_head"])

    expected_transaction = context.absolute(EVIDENCE_BASE) / f"{transaction['transaction_id']}.json"
    require(transaction_path.resolve() == expected_transaction, "transaction path is not canonical")
    transaction_sha256 = digest_file(transaction_path)

    operator = transaction["operator_authorization"]
    authorization_path = context.repository / operator["record_path"]
    authorization = validate_authorization(
        context,
        transaction,
        authorization_path,
        operator["record_sha256"],
    )
    _backup_manifest, backup_entries = validate_backup(context, transaction, authorization)

    for index, item in enumerate(transaction["files"], start=1):
        source = context.repository / item["source"]
        require(digest_file(source, f"source {index}") == item["source_sha256"], f"source digest mismatch at {index}")
        destination_state(context, item, backup_entries[index - 1], index)

    consumption_path, receipt_path = consumption_and_receipt_paths(context, transaction["transaction_id"])
    require(not os.path.lexists(consumption_path), "authorization consumption record already exists")
    require(not os.path.lexists(receipt_path), "installation receipt already exists")

    request_before = snapshot_path(context.absolute(RUNTIME_REQUEST))
    evidence_before = snapshot_path(context.absolute(RUNTIME_EVIDENCE))
    services_before = running_services(context)
    service_before = assert_service_safe(context, unit_must_exist=False)

    lock_path = context.lock_path
    require(lock_path.parent.is_dir(), f"lock directory missing: {lock_path.parent}")
    lock_flags = os.O_RDWR | os.O_CREAT
    if hasattr(os, "O_NOFOLLOW"):
        lock_flags |= os.O_NOFOLLOW
    lock_descriptor = os.open(lock_path, lock_flags, 0o600)
    try:
        fcntl.flock(lock_descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError as exc:
        os.close(lock_descriptor)
        raise ExecutionError("another K21D installation transaction holds the lock") from exc

    installed_indices: list[int] = []
    created_directories: list[Path] = []
    unit_changed = False
    daemon_reload_performed = False
    consumption_written = False
    try:
        require(not os.path.lexists(consumption_path), "authorization consumed while waiting for lock")
        require(not os.path.lexists(receipt_path), "receipt appeared while waiting for lock")
        consumption = {
            "schema": CONSUMPTION_SCHEMA,
            "transaction_id": transaction["transaction_id"],
            "transaction_sha256": transaction_sha256,
            "authorization_id": authorization["authorization_id"],
            "authorization_path": operator["record_path"],
            "authorization_sha256": operator["record_sha256"],
            "consumed_at": utc_text(now),
            "single_use": True,
            "consumed_before_mutation": True,
            "status": "CONSUMED_FOR_ONE_INSTALLATION_ATTEMPT",
        }
        atomic_json_exclusive(consumption_path, consumption)
        consumption_written = True

        unit_item = transaction["files"][-1]
        unit_destination = context.absolute(unit_item["destination"])
        unit_changed = (
            not unit_item["destination_preexisting"]
            or digest_file(unit_destination) != unit_item["source_sha256"]
        )

        for index, item in enumerate(transaction["files"], start=1):
            source = context.repository / item["source"]
            destination = context.absolute(item["destination"])
            atomic_install(
                context,
                source,
                destination,
                item["mode"],
                created_directories,
                item["source_sha256"],
            )
            installed_indices.append(index)
            require(digest_file(destination) == item["source_sha256"], f"immediate install verification failed at {index}")

        if unit_changed:
            run_checked(context, ["systemctl", "daemon-reload"], "conditional daemon-reload")
            daemon_reload_performed = True

        verify_installed(context, transaction)
        unit_physical = context.absolute("/etc/systemd/system/spot-controlled-read-observe.service")
        run_checked(context, ["systemd-analyze", "verify", str(unit_physical)], "unit verification")
        service_after = assert_service_safe(context, unit_must_exist=True)
        regressions = run_offline_regressions(context)
        require(snapshot_path(context.absolute(RUNTIME_REQUEST)) == request_before, "runtime request changed")
        require(snapshot_path(context.absolute(RUNTIME_EVIDENCE)) == evidence_before, "runtime observation evidence changed")
        require(running_services(context) == services_before, "unrelated running-service state changed")

        receipt = {
            "schema": RECEIPT_SCHEMA,
            "transaction_id": transaction["transaction_id"],
            "transaction_sha256": transaction_sha256,
            "authorization_id": authorization["authorization_id"],
            "authorization_sha256": operator["record_sha256"],
            "backup_manifest_id": transaction["backup"]["manifest_id"],
            "backup_manifest_sha256": transaction["backup"]["manifest_sha256"],
            "backup_binding_id": transaction["backup"]["binding_id"],
            "rollback_binding_id": transaction["rollback"]["binding_id"],
            "repository_head": transaction["repository_head"],
            "completed_at": utc_text(context.now()),
            "installed_files": [
                {
                    "destination": item["destination"],
                    "sha256": item["source_sha256"],
                    "mode": item["mode"],
                    "owner": "root",
                    "group": "root",
                }
                for item in transaction["files"]
            ],
            "service_state_before": service_before,
            "service_state_after": service_after,
            "unit_changed": unit_changed,
            "daemon_reload_performed": daemon_reload_performed,
            "offline_regressions": regressions,
            "request_state_unchanged": True,
            "runtime_evidence_unchanged": True,
            "unrelated_running_services_unchanged": True,
            "activation_performed": False,
            "enablement_performed": False,
            "scheduling_performed": False,
            "production_observation_performed": False,
            "execution_allowed": False,
            "mutation_authority": False,
            "outcome": "INSTALLED_DORMANT",
        }
        atomic_json_exclusive(receipt_path, receipt)
        return receipt
    except (OSError, ExecutionError) as exc:
        rollback = rollback_installation(
            context,
            transaction,
            authorization,
            backup_entries,
            installed_indices,
            created_directories,
            unit_changed and bool(installed_indices),
        ) if installed_indices else {"restored": [], "failures": [], "succeeded": True}
        failure_receipt = {
            "schema": RECEIPT_SCHEMA,
            "transaction_id": transaction["transaction_id"],
            "transaction_sha256": transaction_sha256,
            "authorization_id": authorization["authorization_id"],
            "authorization_sha256": operator["record_sha256"],
            "failed_at": utc_text(context.now()),
            "failure": str(exc),
            "authorization_consumed": consumption_written,
            "rollback": rollback,
            "daemon_reload_performed_before_failure": daemon_reload_performed,
            "activation_performed": False,
            "enablement_performed": False,
            "scheduling_performed": False,
            "production_observation_performed": False,
            "execution_allowed": False,
            "mutation_authority": False,
            "outcome": "ROLLED_BACK" if rollback["succeeded"] else "ROLLBACK_FAILED",
        }
        if consumption_written and not os.path.lexists(receipt_path):
            try:
                atomic_json_exclusive(receipt_path, failure_receipt)
            except (OSError, ExecutionError) as journal_exc:
                raise ExecutionError(f"{exc}; rollback={rollback}; receipt failure={journal_exc}") from journal_exc
        raise ExecutionError(f"{exc}; rollback_succeeded={rollback['succeeded']}") from exc
    finally:
        fcntl.flock(lock_descriptor, fcntl.LOCK_UN)
        os.close(lock_descriptor)


def offline_self_test() -> None:
    require(len(FILE_MAP) == 8, "mapping count changed")
    require(len({entry[0] for entry in FILE_MAP}) == 8, "duplicate source")
    require(len({entry[1] for entry in FILE_MAP}) == 8, "duplicate destination")
    require(FILE_MAP[-1][1] == "/etc/systemd/system/spot-controlled-read-observe.service", "unit destination changed")
    for _source, destination, mode in FILE_MAP:
        require(destination.startswith(("/usr/local/lib/spot/observe/", "/etc/spot/observe/", "/etc/systemd/system/")), "destination escaped fixed roots")
        require(mode in {"0755", "0644"}, "unexpected destination mode")


def main() -> int:
    parser = argparse.ArgumentParser(description="K21D installation-only executor")
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--offline-self-test", action="store_true")
    action.add_argument("--execute", action="store_true")
    parser.add_argument("--transaction", type=Path)
    parser.add_argument("--repository", type=Path, default=LIVE_REPOSITORY)
    args = parser.parse_args()

    if args.offline_self_test:
        require(args.transaction is None, "offline self-test takes no transaction")
        try:
            offline_self_test()
        except ExecutionError as exc:
            print(f"[DENY] K21D executor self-test failed: {exc}", file=sys.stderr)
            return 2
        print("[PASS] K21D live executor static self-test")
        print("installation_performed=false")
        print("daemon_reload_performed=false")
        print("activation_authorized=false")
        print("execution_allowed=false")
        print("mutation_authority=false")
        return 0

    if args.transaction is None:
        parser.error("--execute requires --transaction")

    context = ExecutionContext(
        repository=args.repository,
        system_root=Path("/"),
        lock_path=LOCK_PATH,
        command_runner=default_runner,
        now=lambda: datetime.now(timezone.utc),
        hostname=socket.gethostname,
        live=True,
    )
    try:
        receipt = execute_transaction(context, args.transaction.resolve())
    except (OSError, ExecutionError) as exc:
        print(f"[DENY] K21D installation failed closed: {exc}", file=sys.stderr)
        print("activation_performed=false", file=sys.stderr)
        print("enablement_performed=false", file=sys.stderr)
        print("scheduling_performed=false", file=sys.stderr)
        print("production_observation_performed=false", file=sys.stderr)
        print("execution_allowed=false", file=sys.stderr)
        print("mutation_authority=false", file=sys.stderr)
        return 2

    print("[PASS] K21D installation-only transaction complete")
    print(f"transaction_id={receipt['transaction_id']}")
    print("observer_installed=true")
    print("observer_active=false")
    print("observer_enabled=false")
    print("observer_scheduled=false")
    print("production_observation_performed=false")
    print("execution_allowed=false")
    print("mutation_authority=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
