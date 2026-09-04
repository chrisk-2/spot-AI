#!/usr/bin/env python3
"""Execute one separately authorized Post-2.39 K21D storage correction.

The live path is deliberately narrow: Spot Core may preserve three reviewed
records, install two reviewed NFSv4 mount units, and activate only those two
mounts.  It never changes the parent collective mount, restarts Docker, or
installs/activates K21D itself.
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
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Sequence


LIVE_REPOSITORY = Path("/home/ogre/spot-stack")
BACKUP_BASE = Path("/mnt/collective/backups/spot-core/post239-k21d-storage")
EVIDENCE_BASE = Path("/mnt/collective/logs/spot/actions/post239-k21d-storage")
LOCK_PATH = Path("/run/lock/spot-post239-k21d-storage.lock")
TRANSACTION_VALIDATOR = (
    "watch/storage/post239-k21d-scoped-nfs-storage-validate.py"
)
EXECUTOR_PATH = "watch/storage/post239-k21d-scoped-nfs-storage.py"
RUNTIME_DRIFT = "starfleet-ui/public/status.json"
PARENT_TARGET = "/mnt/collective"
PARENT_SOURCE = "//unimatrix6/docker"
PARENT_FSTYPE = "cifs"
NFS_EXPORT_ROOT = "192.168.50.10:/volume1/spotvault"
NFS_MOUNT_OPTIONS = (
    "rw,vers=4.0,proto=tcp,hard,timeo=600,retrans=2,sec=sys,"
    "nosuid,nodev,noexec,noatime"
)
REQUIRED_EFFECTIVE_NFS_OPTIONS = {
    "rw",
    "hard",
    "proto=tcp",
    "sec=sys",
    "nosuid",
    "nodev",
    "noexec",
    "noatime",
    "vers=4.0",
}
BACKUP_SCHEMA = "starfleet.post239.k21d_scoped_nfs_storage_backup.v1"
BACKUP_BINDING_SCHEMA = (
    "starfleet.post239.k21d_scoped_nfs_storage_backup_binding.v1"
)
CONSUMPTION_SCHEMA = (
    "starfleet.post239.k21d_scoped_nfs_storage_authorization_consumption.v1"
)
RECEIPT_SCHEMA = "starfleet.post239.k21d_scoped_nfs_storage_receipt.v1"
MAX_FILE_BYTES = 4 * 1024 * 1024
GIT = "/usr/bin/git"
FINDMNT = "/usr/bin/findmnt"
SYSTEMCTL = "/usr/bin/systemctl"
MOUNT = "/usr/bin/mount"
UMOUNT = "/usr/bin/umount"
UNSHARE = "/usr/bin/unshare"

LIVE_K21D_PATHS = (
    "/usr/local/lib/spot/observe/controlled-read-observe.py",
    "/usr/local/lib/spot/observe/controlled_read_observe_validation_v1.py",
    "/usr/local/lib/spot/observe/controlled-read-observe-request-validate.py",
    "/usr/local/lib/spot/observe/controlled-read-observe-evidence-validate.py",
    "/etc/spot/observe/controlled-read-observe-allowlist-v1.json",
    "/etc/spot/observe/controlled-read-observe-request-schema-v1.json",
    "/etc/spot/observe/controlled-read-observe-evidence-schema-v1.json",
    "/etc/systemd/system/spot-controlled-read-observe.service",
)


class ExecutionError(RuntimeError):
    """A fail-closed storage transaction denial or execution failure."""


@dataclass
class CommandResult:
    returncode: int
    stdout: str = ""
    stderr: str = ""


CommandRunner = Callable[[Sequence[str], Path | None], CommandResult]
PathResolver = Callable[[Path], Path]
NfsPreparer = Callable[["ExecutionContext", dict[str, Any], Path, str], dict[str, Any]]
ValidationHook = Callable[[dict[str, Any], Path, datetime], None]


@dataclass
class ExecutionContext:
    repository: Path
    system_root: Path
    command_runner: CommandRunner
    now: Callable[[], datetime]
    live: bool
    path_resolver: PathResolver | None = None
    nfs_preparer: NfsPreparer | None = None
    validation_hook: ValidationHook | None = None

    def absolute(self, path: str | Path) -> Path:
        logical = Path(path)
        require(logical.is_absolute(), f"absolute path required: {logical}")
        if self.path_resolver is not None:
            return self.path_resolver(logical)
        if self.system_root == Path("/"):
            return logical
        return self.system_root / logical.relative_to("/")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ExecutionError(message)


def utc_text(value: datetime | None = None) -> str:
    current = value or datetime.now(timezone.utc)
    return current.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def default_runner(arguments: Sequence[str], cwd: Path | None) -> CommandResult:
    completed = subprocess.run(
        list(arguments),
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    return CommandResult(completed.returncode, completed.stdout, completed.stderr)


def run_checked(
    context: ExecutionContext,
    arguments: Sequence[str],
    purpose: str,
    *,
    cwd: Path | None = None,
) -> CommandResult:
    result = context.command_runner(arguments, cwd)
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "no output"
        raise ExecutionError(f"{purpose} failed ({result.returncode}): {detail}")
    return result


def regular_lstat(path: Path, label: str) -> os.stat_result:
    try:
        info = path.lstat()
    except OSError as exc:
        raise ExecutionError(f"{label} missing: {path}") from exc
    require(stat.S_ISREG(info.st_mode), f"{label} is not a regular file: {path}")
    return info


def directory_lstat(path: Path, label: str) -> os.stat_result:
    try:
        info = path.lstat()
    except OSError as exc:
        raise ExecutionError(f"{label} missing: {path}") from exc
    require(stat.S_ISDIR(info.st_mode), f"{label} is not a directory: {path}")
    return info


def digest_file(path: Path, label: str = "file") -> str:
    info = regular_lstat(path, label)
    require(info.st_size <= MAX_FILE_BYTES, f"{label} exceeds size limit: {path}")
    value = hashlib.sha256()
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags)
    try:
        opened = os.fstat(descriptor)
        require(stat.S_ISREG(opened.st_mode), f"{label} changed type: {path}")
        require(
            (opened.st_dev, opened.st_ino) == (info.st_dev, info.st_ino),
            f"{label} changed while opening: {path}",
        )
        while True:
            block = os.read(descriptor, 1024 * 1024)
            if not block:
                break
            value.update(block)
        closed = os.fstat(descriptor)
        require(
            (closed.st_size, closed.st_mtime_ns)
            == (opened.st_size, opened.st_mtime_ns),
            f"{label} changed while hashing: {path}",
        )
    finally:
        os.close(descriptor)
    return value.hexdigest()


def read_regular_bytes(path: Path, label: str) -> bytes:
    info = regular_lstat(path, label)
    require(info.st_size <= MAX_FILE_BYTES, f"{label} exceeds size limit: {path}")
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags)
    try:
        opened = os.fstat(descriptor)
        require(stat.S_ISREG(opened.st_mode), f"{label} changed type: {path}")
        require(
            (opened.st_dev, opened.st_ino) == (info.st_dev, info.st_ino),
            f"{label} changed while opening: {path}",
        )
        chunks: list[bytes] = []
        remaining = info.st_size
        while remaining:
            block = os.read(descriptor, min(remaining, 1024 * 1024))
            require(bool(block), f"short read: {path}")
            chunks.append(block)
            remaining -= len(block)
        require(not os.read(descriptor, 1), f"{label} changed while reading: {path}")
        closed = os.fstat(descriptor)
        require(
            (closed.st_size, closed.st_mtime_ns)
            == (opened.st_size, opened.st_mtime_ns),
            f"{label} changed while reading: {path}",
        )
        return b"".join(chunks)
    finally:
        os.close(descriptor)


def read_json(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(read_regular_bytes(path, label).decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ExecutionError(f"invalid {label}: {path}") from exc
    require(isinstance(payload, dict), f"{label} must be a JSON object")
    return payload


def fsync_directory(path: Path) -> None:
    descriptor = os.open(
        path,
        os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0),
    )
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def assert_no_symlink_components(path: Path, label: str) -> None:
    require(path.is_absolute(), f"absolute path required for {label}: {path}")
    cursor = Path("/")
    for component in path.parts[1:]:
        cursor /= component
        if not os.path.lexists(cursor):
            break
        try:
            info = cursor.lstat()
        except OSError as exc:
            raise ExecutionError(f"cannot inspect {label}: {cursor}") from exc
        require(not stat.S_ISLNK(info.st_mode), f"{label} traverses a symlink: {cursor}")


def secure_makedirs(path: Path, mode: int = 0o700) -> list[Path]:
    """Create absent absolute path components without following leaf symlinks."""

    require(path.is_absolute(), f"absolute directory required: {path}")
    assert_no_symlink_components(path, "directory path")
    missing: list[Path] = []
    cursor = path
    while not os.path.lexists(cursor):
        missing.append(cursor)
        require(cursor.parent != cursor, f"cannot resolve directory parent: {path}")
        cursor = cursor.parent
    directory_lstat(cursor, "existing directory ancestor")
    created: list[Path] = []
    for candidate in reversed(missing):
        os.mkdir(candidate, mode)
        fsync_directory(candidate.parent)
        created.append(candidate)
    directory_lstat(path, "directory")
    return created


def write_bytes_exclusive(
    path: Path,
    data: bytes,
    mode: int,
    *,
    uid: int | None = None,
    gid: int | None = None,
) -> None:
    require(path.is_absolute(), f"absolute output path required: {path}")
    assert_no_symlink_components(path.parent, "output path")
    directory_lstat(path.parent, "output directory")
    assert_absent(path, "exclusive output")
    temporary_descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
    )
    temporary = Path(temporary_name)
    linked = False
    try:
        os.fchmod(temporary_descriptor, mode)
        if uid is not None and gid is not None:
            os.fchown(temporary_descriptor, uid, gid)
        view = memoryview(data)
        while view:
            written = os.write(temporary_descriptor, view)
            require(written > 0, f"short write: {path}")
            view = view[written:]
        os.fsync(temporary_descriptor)
        os.close(temporary_descriptor)
        temporary_descriptor = -1
        os.link(temporary, path, follow_symlinks=False)
        linked = True
        fsync_directory(path.parent)
    finally:
        if temporary_descriptor >= 0:
            os.close(temporary_descriptor)
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
        if linked:
            fsync_directory(path.parent)
    fsync_directory(path.parent)


def write_json_exclusive(path: Path, payload: dict[str, Any], mode: int = 0o600) -> None:
    data = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8")
    write_bytes_exclusive(path, data, mode)


def load_validator(repository: Path) -> Any:
    path = repository / TRANSACTION_VALIDATOR
    regular_lstat(path, "transaction validator")
    spec = importlib.util.spec_from_file_location("k21d_storage_validator", path)
    require(spec is not None and spec.loader is not None, "cannot load validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate_transaction(
    context: ExecutionContext,
    transaction: dict[str, Any],
) -> None:
    if context.validation_hook is not None:
        context.validation_hook(transaction, context.repository, context.now())
        return
    validator = load_validator(context.repository)
    try:
        validator.validate_transaction(
            transaction,
            context.repository,
            reference_checks=True,
            now=context.now(),
        )
    except (OSError, ValueError) as exc:
        raise ExecutionError(f"transaction validation denied: {exc}") from exc


def git(context: ExecutionContext, *arguments: str) -> str:
    command = [
        GIT,
        "-c",
        f"safe.directory={context.repository}",
        "-C",
        str(context.repository),
        *arguments,
    ]
    return run_checked(context, command, "repository verification").stdout.strip()


def validate_repository(context: ExecutionContext, expected_head: str) -> None:
    if not context.live:
        return
    require(socket.gethostname() == "spot-core", "live execution is restricted to spot-core")
    require(os.geteuid() == 0, "live execution requires root")
    require(context.repository.resolve() == LIVE_REPOSITORY, "wrong live repository")
    require(git(context, "branch", "--show-current") == "main", "wrong branch")
    require(git(context, "rev-parse", "HEAD") == expected_head, "HEAD mismatch")
    require(git(context, "rev-parse", "origin/main") == expected_head, "origin/main mismatch")
    require(not git(context, "diff", "--cached", "--name-only"), "staged changes present")
    require(git(context, "diff", "--name-only") == RUNTIME_DRIFT, "tracked drift boundary changed")
    require(not git(context, "ls-files", "--others", "--exclude-standard"), "untracked files present")


def validate_live_dependencies(context: ExecutionContext) -> None:
    if not context.live:
        return
    for executable in (GIT, FINDMNT, SYSTEMCTL, MOUNT, UMOUNT, UNSHARE):
        require(
            Path(executable).is_file() and os.access(executable, os.X_OK),
            f"required executable unavailable: {executable}",
        )
    nfs_helpers = (Path("/sbin/mount.nfs4"), Path("/usr/sbin/mount.nfs4"))
    require(
        any(path.exists() and os.access(path, os.X_OK) for path in nfs_helpers),
        "NFSv4 mount helper unavailable",
    )


def logical_transaction_path(repository: Path, transaction_id: str) -> Path:
    return repository / "watch/review/bundles" / f"{transaction_id}.json"


def record_paths(context: ExecutionContext, transaction_id: str) -> tuple[Path, Path]:
    evidence = context.absolute(EVIDENCE_BASE)
    return (
        evidence / f"{transaction_id}.consumption.json",
        evidence / f"{transaction_id}.receipt.json",
    )


def assert_absent(path: Path, label: str) -> None:
    require(not os.path.lexists(path), f"{label} already exists: {path}")


def assert_live_k21d_absent(context: ExecutionContext) -> None:
    for path_text in LIVE_K21D_PATHS:
        assert_absent(context.absolute(path_text), "K21D live destination")


def parent_mount(context: ExecutionContext) -> list[tuple[str, str]]:
    result = run_checked(
        context,
        [FINDMNT, "-rn", "-T", PARENT_TARGET, "-o", "SOURCE,FSTYPE"],
        "parent collective mount inspection",
    )
    pairs: list[tuple[str, str]] = []
    for line in result.stdout.splitlines():
        fields = line.split()
        if len(fields) >= 2:
            pairs.append((fields[0], fields[1]))
    require((PARENT_SOURCE, PARENT_FSTYPE) in pairs, "parent collective CIFS mount mismatch")
    return pairs


def exact_mount(context: ExecutionContext, target: str) -> tuple[str, str, set[str]] | None:
    result = context.command_runner(
        [FINDMNT, "-rn", "-M", target, "-o", "SOURCE,FSTYPE,OPTIONS"],
        None,
    )
    if result.returncode != 0 or not result.stdout.strip():
        return None
    lines = [line for line in result.stdout.splitlines() if line.strip()]
    require(len(lines) == 1, f"ambiguous exact mount state: {target}")
    fields = lines[0].split(None, 2)
    require(len(fields) == 3, f"invalid exact mount result: {target}")
    return fields[0], fields[1], set(fields[2].split(","))


def docker_snapshot(context: ExecutionContext) -> dict[str, str]:
    state = run_checked(
        context,
        [SYSTEMCTL, "is-active", "docker.service"],
        "Docker active-state inspection",
    ).stdout.strip()
    require(state == "active", "Docker is not active")
    pid = run_checked(
        context,
        [SYSTEMCTL, "show", "docker.service", "-p", "MainPID", "--value"],
        "Docker PID inspection",
    ).stdout.strip()
    entered = run_checked(
        context,
        [
            SYSTEMCTL,
            "show",
            "docker.service",
            "-p",
            "ActiveEnterTimestampMonotonic",
            "--value",
        ],
        "Docker activation timestamp inspection",
    ).stdout.strip()
    require(pid.isdigit() and int(pid) > 0, "Docker MainPID invalid")
    require(entered.isdigit() and int(entered) > 0, "Docker active timestamp invalid")
    return {"main_pid": pid, "active_enter_timestamp_monotonic": entered}


def unit_state(context: ExecutionContext, unit_name: str) -> dict[str, Any]:
    active_result = context.command_runner([SYSTEMCTL, "is-active", unit_name], None)
    active = active_result.stdout.strip()
    enabled_result = context.command_runner([SYSTEMCTL, "is-enabled", unit_name], None)
    enabled = enabled_result.stdout.strip()
    return {
        "active": active == "active",
        "active_state": active,
        "enabled": enabled == "enabled",
        "enabled_state": enabled,
    }


def validate_initial_state(
    context: ExecutionContext,
    transaction: dict[str, Any],
) -> dict[str, Any]:
    parent = parent_mount(context)
    assert_live_k21d_absent(context)
    fstab = context.absolute("/etc/fstab")
    fstab_info = regular_lstat(fstab, "fstab")
    fstab_sha = digest_file(fstab, "fstab")
    docker = docker_snapshot(context)

    mount_states: list[dict[str, Any]] = []
    for item in transaction["mounts"]:
        require(exact_mount(context, item["target"]) is None, f"scoped target already mounted: {item['target']}")
        installed = context.absolute(item["installed_path"])
        assert_absent(installed, "scoped mount unit")
        state = unit_state(context, item["unit_name"])
        require(not state["active"], f"scoped unit already active: {item['unit_name']}")
        require(not state["enabled"], f"scoped unit already enabled: {item['unit_name']}")
        mount_states.append({**state, "unit_name": item["unit_name"], "unit_file_present": False})

    objects: list[dict[str, Any]] = []
    for item in transaction["preserved_objects"]:
        source = context.absolute(item["source_path"])
        if item["kind"] == "file":
            info = regular_lstat(source, "preserved source")
            require(digest_file(source, "preserved source") == item["sha256"], f"preserved source digest mismatch: {source}")
            entry_count = None
        else:
            info = directory_lstat(source, "preserved source directory")
            entries = list(os.scandir(source))
            require(not entries, f"preserved source directory is not empty: {source}")
            entry_count = 0
        objects.append(
            {
                "kind": item["kind"],
                "path": item["source_path"],
                "sha256": item["sha256"],
                "mode": f"{stat.S_IMODE(info.st_mode):04o}",
                "uid": info.st_uid,
                "gid": info.st_gid,
                "entry_count": entry_count,
            }
        )

    return {
        "parent_mounts": [{"source": source, "fstype": fstype} for source, fstype in parent],
        "fstab": {
            "sha256": fstab_sha,
            "mode": f"{stat.S_IMODE(fstab_info.st_mode):04o}",
            "uid": fstab_info.st_uid,
            "gid": fstab_info.st_gid,
        },
        "docker": docker,
        "mounts": mount_states,
        "preserved_objects": objects,
        "live_k21d_paths_absent": True,
    }


def copy_to_backup(source: Path, destination: Path, label: str) -> dict[str, Any]:
    info = regular_lstat(source, label)
    data = read_regular_bytes(source, label)
    source_sha = hashlib.sha256(data).hexdigest()
    write_bytes_exclusive(destination, data, 0o600)
    require(digest_file(destination, "backup copy") == source_sha, f"backup verification failed: {destination}")
    return {
        "source": str(source),
        "backup_path": str(destination),
        "sha256": source_sha,
        "size": len(data),
        "mode": f"{stat.S_IMODE(info.st_mode):04o}",
        "uid": info.st_uid,
        "gid": info.st_gid,
    }


def create_verified_backup(
    context: ExecutionContext,
    transaction: dict[str, Any],
    transaction_path: Path,
    transaction_sha256: str,
    authorization_path: Path,
    pre_state: dict[str, Any],
) -> dict[str, Any]:
    backup = transaction["backup"]
    base = context.absolute(backup["root"])
    secure_makedirs(base)
    backup_directory = base / backup["backup_id"]
    binding_path = base / f"{backup['binding_id']}.json"
    assert_absent(backup_directory, "transaction backup directory")
    assert_absent(binding_path, "backup binding")
    os.mkdir(backup_directory, 0o700)
    fsync_directory(backup_directory.parent)
    files_directory = backup_directory / "files"
    os.mkdir(files_directory, 0o700)
    fsync_directory(files_directory.parent)

    copied: list[dict[str, Any]] = []
    copied.append(
        copy_to_backup(
            context.absolute("/etc/fstab"),
            files_directory / "01-fstab.backup",
            "fstab",
        )
    )
    file_number = 2
    for item in transaction["preserved_objects"]:
        source = context.absolute(item["source_path"])
        if item["kind"] == "file":
            destination = files_directory / f"{file_number:02d}-{source.name}.backup"
            entry = copy_to_backup(source, destination, "preserved source")
            require(entry["sha256"] == item["sha256"], f"approved source changed: {source}")
            copied.append(entry)
            file_number += 1

    manifest = {
        "schema": BACKUP_SCHEMA,
        "backup_id": backup["backup_id"],
        "binding_id": backup["binding_id"],
        "created_at": utc_text(context.now()),
        "host": "spot-core",
        "repository_head": transaction["repository_head"],
        "transaction_id": transaction["transaction_id"],
        "transaction_path": str(transaction_path),
        "transaction_sha256": transaction_sha256,
        "authorization_id": transaction["operator_authorization"]["authorization_id"],
        "authorization_path": str(authorization_path),
        "authorization_sha256": transaction["operator_authorization"]["record_sha256"],
        "pre_state": pre_state,
        "files": copied,
        "verified": True,
        "status": "VERIFIED_PRECHANGE_BACKUP",
    }
    manifest_path = backup_directory / f"{backup['backup_id']}.manifest.json"
    write_json_exclusive(manifest_path, manifest)
    manifest_sha = digest_file(manifest_path, "backup manifest")

    binding = {
        "schema": BACKUP_BINDING_SCHEMA,
        "binding_id": backup["binding_id"],
        "backup_id": backup["backup_id"],
        "backup_manifest_path": str(manifest_path),
        "backup_manifest_sha256": manifest_sha,
        "transaction_id": transaction["transaction_id"],
        "transaction_sha256": transaction_sha256,
        "authorization_id": transaction["operator_authorization"]["authorization_id"],
        "authorization_sha256": transaction["operator_authorization"]["record_sha256"],
        "verified_at": utc_text(context.now()),
        "verified": True,
        "status": "BOUND_VERIFIED_PRECHANGE_BACKUP",
    }
    write_json_exclusive(binding_path, binding)
    binding_sha = digest_file(binding_path, "backup binding")

    require(read_json(manifest_path, "backup manifest") == manifest, "backup manifest readback mismatch")
    require(read_json(binding_path, "backup binding") == binding, "backup binding readback mismatch")
    for entry in copied:
        require(
            digest_file(Path(entry["backup_path"]), "backup copy") == entry["sha256"],
            "backup copy changed after binding",
        )
    return {
        "backup_id": backup["backup_id"],
        "binding_id": backup["binding_id"],
        "manifest_path": str(manifest_path),
        "manifest_sha256": manifest_sha,
        "binding_path": str(binding_path),
        "binding_sha256": binding_sha,
        "files": copied,
        "verified": True,
    }


def validate_backup_readback(backup_record: dict[str, Any]) -> None:
    require(backup_record.get("verified") is True, "backup record is not verified")
    manifest_path = Path(backup_record["manifest_path"])
    binding_path = Path(backup_record["binding_path"])
    require(digest_file(manifest_path, "backup manifest") == backup_record["manifest_sha256"], "backup manifest changed")
    require(digest_file(binding_path, "backup binding") == backup_record["binding_sha256"], "backup binding changed")
    for entry in backup_record["files"]:
        require(digest_file(Path(entry["backup_path"]), "backup copy") == entry["sha256"], "backup copy changed")


def build_consumption(
    context: ExecutionContext,
    transaction: dict[str, Any],
    transaction_sha256: str,
    backup_record: dict[str, Any],
) -> dict[str, Any]:
    operator = transaction["operator_authorization"]
    return {
        "schema": CONSUMPTION_SCHEMA,
        "transaction_id": transaction["transaction_id"],
        "transaction_sha256": transaction_sha256,
        "authorization_id": operator["authorization_id"],
        "authorization_path": operator["record_path"],
        "authorization_sha256": operator["record_sha256"],
        "backup_id": backup_record["backup_id"],
        "backup_manifest_path": backup_record["manifest_path"],
        "backup_manifest_sha256": backup_record["manifest_sha256"],
        "backup_binding_id": backup_record["binding_id"],
        "backup_binding_path": backup_record["binding_path"],
        "backup_binding_sha256": backup_record["binding_sha256"],
        "consumed_at": utc_text(context.now()),
        "single_use": True,
        "execution_allowed": False,
        "mutation_authority": False,
        "status": "CONSUMED_FOR_ONE_SCOPED_NFS_STORAGE_ATTEMPT",
    }


def validate_consumption(
    path: Path,
    transaction: dict[str, Any],
    transaction_sha256: str,
) -> dict[str, Any]:
    consumption = read_json(path, "authorization consumption")
    require(consumption.get("schema") == CONSUMPTION_SCHEMA, "wrong consumption schema")
    require(consumption.get("transaction_id") == transaction["transaction_id"], "consumption transaction mismatch")
    require(consumption.get("transaction_sha256") == transaction_sha256, "consumption transaction digest mismatch")
    require(consumption.get("authorization_id") == transaction["operator_authorization"]["authorization_id"], "consumption authorization mismatch")
    require(consumption.get("authorization_sha256") == transaction["operator_authorization"]["record_sha256"], "consumption authorization digest mismatch")
    require(consumption.get("single_use") is True, "consumption is not single-use")
    require(consumption.get("execution_allowed") is False, "consumption grants global execution")
    require(consumption.get("mutation_authority") is False, "consumption grants global mutation")
    require(consumption.get("status") == "CONSUMED_FOR_ONE_SCOPED_NFS_STORAGE_ATTEMPT", "consumption status invalid")
    return consumption


def safe_relative(value: str) -> PurePosixPath:
    relative = PurePosixPath(value)
    require(not relative.is_absolute(), f"NFS destination must be relative: {value}")
    require(relative.parts and all(part not in ("", ".", "..") for part in relative.parts), f"unsafe NFS destination: {value}")
    return relative


def ensure_secure_nfs_parent(root: Path, relative_parent: PurePosixPath) -> list[Path]:
    cursor = root
    created: list[Path] = []
    for component in relative_parent.parts:
        candidate = cursor / component
        if os.path.lexists(candidate):
            info = candidate.lstat()
            require(stat.S_ISDIR(info.st_mode), f"NFS parent is not a directory: {candidate}")
            require(not candidate.is_symlink(), f"NFS parent is a symlink: {candidate}")
            require(info.st_uid == 0 and info.st_gid == 0, f"NFS parent ownership is unsafe: {candidate}")
            require(stat.S_IMODE(info.st_mode) & 0o022 == 0, f"NFS parent is writable by group/other: {candidate}")
        else:
            os.mkdir(candidate, 0o700)
            os.chown(candidate, 0, 0, follow_symlinks=False)
            os.chmod(candidate, 0o700, follow_symlinks=False)
            fsync_directory(cursor)
            created.append(candidate)
        cursor = candidate
    return created


def create_nfs_object(
    context: ExecutionContext,
    export_root: Path,
    item: dict[str, Any],
) -> dict[str, Any]:
    relative = safe_relative(item["destination_relative"])
    destination = export_root.joinpath(*relative.parts)
    ensure_secure_nfs_parent(export_root, relative.parent)
    assert_absent(destination, "NFS destination")
    if item["kind"] == "directory":
        source = context.absolute(item["source_path"])
        directory_lstat(source, "preserved source directory")
        require(not list(os.scandir(source)), "preserved source directory is no longer empty")
        os.mkdir(destination, 0o700)
        os.chown(destination, 0, 0, follow_symlinks=False)
        os.chmod(destination, 0o700, follow_symlinks=False)
        fsync_directory(destination.parent)
        info = directory_lstat(destination, "NFS directory")
        require(stat.S_IMODE(info.st_mode) == 0o700, "NFS directory mode mismatch")
        require(info.st_uid == 0 and info.st_gid == 0, "NFS directory ownership mismatch")
        actual_sha = None
    else:
        source = context.absolute(item["source_path"])
        data = read_regular_bytes(source, "preserved source")
        require(hashlib.sha256(data).hexdigest() == item["sha256"], "preserved source changed before NFS copy")
        write_bytes_exclusive(destination, data, 0o400, uid=0, gid=0)
        info = regular_lstat(destination, "NFS record")
        actual_sha = digest_file(destination, "NFS record")
        require(actual_sha == item["sha256"], "NFS record digest mismatch")
        require(stat.S_IMODE(info.st_mode) == 0o400, "NFS record mode mismatch")
        require(info.st_uid == 0 and info.st_gid == 0, "NFS record ownership mismatch")
    return {
        "kind": item["kind"],
        "destination_relative": item["destination_relative"],
        "sha256": actual_sha,
        "mode": f"{stat.S_IMODE(info.st_mode):04o}",
        "uid": info.st_uid,
        "gid": info.st_gid,
        "created": True,
    }


def prepare_nfs_in_private_namespace(
    context: ExecutionContext,
    transaction: dict[str, Any],
    transaction_path: Path,
    transaction_sha256: str,
    consumption_path: Path,
) -> dict[str, Any]:
    """Internal root-only helper run inside a private mount namespace."""

    require(context.live, "internal NFS preparation is live-only")
    validate_repository(context, transaction["repository_head"])
    validate_live_dependencies(context)
    validate_transaction(context, transaction)
    require(transaction_path == logical_transaction_path(context.repository, transaction["transaction_id"]), "transaction path is not canonical")
    require(digest_file(transaction_path, "transaction") == transaction_sha256, "transaction changed before NFS preparation")
    expected_consumption, _receipt = record_paths(context, transaction["transaction_id"])
    require(consumption_path == expected_consumption, "consumption path mismatch")
    validate_consumption(consumption_path, transaction, transaction_sha256)
    parent_mount(context)
    assert_live_k21d_absent(context)

    mountpoint = Path(tempfile.mkdtemp(prefix="spot-k21d-storage.", dir="/run"))
    mounted = False
    objects: list[dict[str, Any]] = []
    cleanup_error: str | None = None
    try:
        run_checked(
            context,
            [
                MOUNT,
                "-t",
                "nfs4",
                "-o",
                NFS_MOUNT_OPTIONS,
                NFS_EXPORT_ROOT,
                str(mountpoint),
            ],
            "private NFS export-root mount",
        )
        mounted = True
        mounted_view = exact_mount(context, str(mountpoint))
        require(mounted_view is not None, "private NFS mount not visible")
        source, fstype, options = mounted_view
        require(source == NFS_EXPORT_ROOT, "private NFS source mismatch")
        require(fstype == "nfs4", "private NFS filesystem mismatch")
        require(REQUIRED_EFFECTIVE_NFS_OPTIONS <= options, "private NFS mount options incomplete")
        for item in transaction["preserved_objects"]:
            objects.append(create_nfs_object(context, mountpoint, item))
        fsync_directory(mountpoint)
    finally:
        if mounted:
            result = context.command_runner([UMOUNT, "--", str(mountpoint)], None)
            if result.returncode != 0:
                cleanup_error = result.stderr.strip() or result.stdout.strip() or "no output"
            mounted = exact_mount(context, str(mountpoint)) is not None
        if not mounted:
            try:
                mountpoint.rmdir()
            except OSError as exc:
                cleanup_error = cleanup_error or str(exc)
    require(not mounted, f"private NFS mount cleanup failed: {cleanup_error}")
    require(not mountpoint.exists(), f"private NFS directory cleanup failed: {cleanup_error}")
    return {
        "source": NFS_EXPORT_ROOT,
        "objects": objects,
        "temporary_mount_removed": True,
        "persistent_probe_artifact": False,
    }


def invoke_live_nfs_preparer(
    context: ExecutionContext,
    transaction: dict[str, Any],
    transaction_path: Path,
    transaction_sha256: str,
) -> dict[str, Any]:
    consumption_path, _receipt_path = record_paths(context, transaction["transaction_id"])
    executor = context.repository / EXECUTOR_PATH
    result = run_checked(
        context,
        [
            UNSHARE,
            "--mount",
            "--propagation",
            "private",
            sys.executable,
            str(executor),
            "--internal-prepare-nfs",
            "--transaction",
            str(transaction_path),
            "--transaction-sha256",
            transaction_sha256,
            "--consumption",
            str(consumption_path),
            "--repository",
            str(context.repository),
        ],
        "isolated NFS preparation",
    )
    try:
        report = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise ExecutionError("isolated NFS preparation returned invalid JSON") from exc
    require(isinstance(report, dict), "isolated NFS report must be an object")
    require(report.get("temporary_mount_removed") is True, "isolated NFS cleanup unverified")
    require(len(report.get("objects", [])) == 3, "isolated NFS object count mismatch")
    return report


def prepare_nfs(
    context: ExecutionContext,
    transaction: dict[str, Any],
    transaction_path: Path,
    transaction_sha256: str,
) -> dict[str, Any]:
    if context.nfs_preparer is not None:
        return context.nfs_preparer(context, transaction, transaction_path, transaction_sha256)
    return invoke_live_nfs_preparer(context, transaction, transaction_path, transaction_sha256)


def install_units(
    context: ExecutionContext,
    transaction: dict[str, Any],
    runtime: dict[str, Any],
) -> None:
    for item in transaction["mounts"]:
        source = context.repository / item["template_path"]
        destination = context.absolute(item["installed_path"])
        data = read_regular_bytes(source, "mount unit template")
        require(hashlib.sha256(data).hexdigest() == item["template_sha256"], "mount unit template changed")
        secure_makedirs(destination.parent, 0o755)
        assert_absent(destination, "installed mount unit")
        write_bytes_exclusive(destination, data, 0o644, uid=0, gid=0)
        require(digest_file(destination, "installed mount unit") == item["template_sha256"], "installed mount unit digest mismatch")
        runtime["installed_units"].append(item["unit_name"])

    run_checked(context, [SYSTEMCTL, "daemon-reload"], "systemd daemon reload")
    runtime["daemon_reload_performed"] = True
    for item in transaction["mounts"]:
        unit_name = item["unit_name"]
        run_checked(context, [SYSTEMCTL, "enable", unit_name], "scoped mount enable")
        runtime["enabled_units"].append(unit_name)
    for item in transaction["mounts"]:
        unit_name = item["unit_name"]
        run_checked(context, [SYSTEMCTL, "start", unit_name], "scoped mount start")
        runtime["started_units"].append(unit_name)


def verify_visible_object(context: ExecutionContext, item: dict[str, Any]) -> dict[str, Any]:
    path = context.absolute(item["source_path"])
    if item["kind"] == "file":
        info = regular_lstat(path, "mounted NFS record")
        actual_sha = digest_file(path, "mounted NFS record")
        require(actual_sha == item["sha256"], f"mounted NFS record digest mismatch: {path}")
    else:
        info = directory_lstat(path, "mounted NFS directory")
        require(not list(os.scandir(path)), f"mounted NFS directory is not empty: {path}")
        actual_sha = None
    require(f"{stat.S_IMODE(info.st_mode):04o}" == item["mode"], f"mounted NFS mode mismatch: {path}")
    require(info.st_uid == item["uid"] and info.st_gid == item["gid"], f"mounted NFS ownership mismatch: {path}")
    return {
        "path": item["source_path"],
        "kind": item["kind"],
        "sha256": actual_sha,
        "mode": f"{stat.S_IMODE(info.st_mode):04o}",
        "uid": info.st_uid,
        "gid": info.st_gid,
    }


def verify_post_state(
    context: ExecutionContext,
    transaction: dict[str, Any],
    pre_state: dict[str, Any],
) -> dict[str, Any]:
    parent_mount(context)
    require(digest_file(context.absolute("/etc/fstab"), "fstab") == pre_state["fstab"]["sha256"], "fstab changed")
    require(docker_snapshot(context) == pre_state["docker"], "Docker restarted or changed")
    assert_live_k21d_absent(context)

    mounts: list[dict[str, Any]] = []
    for item in transaction["mounts"]:
        installed = context.absolute(item["installed_path"])
        info = regular_lstat(installed, "installed mount unit")
        require(digest_file(installed, "installed mount unit") == item["template_sha256"], "installed mount unit changed")
        require(stat.S_IMODE(info.st_mode) == 0o644 and info.st_uid == 0 and info.st_gid == 0, "installed mount unit metadata mismatch")
        state = unit_state(context, item["unit_name"])
        require(state["active"], f"scoped mount inactive: {item['unit_name']}")
        require(state["enabled"], f"scoped mount disabled: {item['unit_name']}")
        view = exact_mount(context, item["target"])
        require(view is not None, f"scoped mount missing: {item['target']}")
        source, fstype, options = view
        require(source == item["source"], f"scoped mount source mismatch: {item['target']}")
        require(fstype == "nfs4", f"scoped mount filesystem mismatch: {item['target']}")
        require(REQUIRED_EFFECTIVE_NFS_OPTIONS <= options, f"scoped mount options incomplete: {item['target']}")
        mounts.append(
            {
                "unit_name": item["unit_name"],
                "source": source,
                "target": item["target"],
                "fstype": fstype,
                "required_options_verified": True,
                "active": True,
                "enabled": True,
                "unit_sha256": item["template_sha256"],
                "unit_mode": "0644",
                "unit_uid": 0,
                "unit_gid": 0,
            }
        )

    objects = [verify_visible_object(context, item) for item in transaction["preserved_objects"]]
    return {
        "parent_collective_unchanged": True,
        "fstab_unchanged": True,
        "docker_unchanged": True,
        "live_k21d_paths_absent": True,
        "mounts": mounts,
        "objects": objects,
    }


def remove_installed_unit_if_unchanged(
    context: ExecutionContext,
    transaction: dict[str, Any],
    unit_name: str,
) -> bool:
    item = next(entry for entry in transaction["mounts"] if entry["unit_name"] == unit_name)
    installed = context.absolute(item["installed_path"])
    if not os.path.lexists(installed):
        return False
    regular_lstat(installed, "rollback mount unit")
    require(digest_file(installed, "rollback mount unit") == item["template_sha256"], f"rollback refuses changed unit: {unit_name}")
    installed.unlink()
    fsync_directory(installed.parent)
    return True


def rollback_units(
    context: ExecutionContext,
    transaction: dict[str, Any],
    runtime: dict[str, Any],
    pre_state: dict[str, Any],
) -> dict[str, Any]:
    stopped: list[str] = []
    disabled: list[str] = []
    removed: list[str] = []
    failures: list[str] = []

    for item in reversed(transaction["mounts"]):
        unit_name = item["unit_name"]
        installed_path = context.absolute(item["installed_path"])
        if (
            unit_name not in runtime["installed_units"]
            and not os.path.lexists(installed_path)
        ):
            continue
        try:
            state = unit_state(context, unit_name)
            mounted = exact_mount(context, item["target"]) is not None
            if state["active"] or mounted:
                run_checked(context, [SYSTEMCTL, "stop", unit_name], "rollback scoped mount stop")
                stopped.append(unit_name)
        except (OSError, ExecutionError) as exc:
            failures.append(str(exc))
    for item in reversed(transaction["mounts"]):
        unit_name = item["unit_name"]
        installed_path = context.absolute(item["installed_path"])
        if (
            unit_name not in runtime["installed_units"]
            and not os.path.lexists(installed_path)
        ):
            continue
        try:
            state = unit_state(context, unit_name)
            if state["enabled"] or unit_name in runtime["enabled_units"]:
                run_checked(context, [SYSTEMCTL, "disable", unit_name], "rollback scoped mount disable")
                disabled.append(unit_name)
        except (OSError, ExecutionError) as exc:
            failures.append(str(exc))
    for item in reversed(transaction["mounts"]):
        unit_name = item["unit_name"]
        try:
            state = unit_state(context, unit_name)
            require(
                not state["active"] and exact_mount(context, item["target"]) is None,
                f"rollback retains unit while mount is active: {unit_name}",
            )
            require(
                not state["enabled"],
                f"rollback retains enabled unit: {unit_name}",
            )
            if remove_installed_unit_if_unchanged(context, transaction, unit_name):
                removed.append(unit_name)
        except (OSError, ExecutionError) as exc:
            failures.append(str(exc))
    if removed:
        try:
            run_checked(context, [SYSTEMCTL, "daemon-reload"], "rollback daemon reload")
        except (OSError, ExecutionError) as exc:
            failures.append(str(exc))

    for item in transaction["mounts"]:
        try:
            require(exact_mount(context, item["target"]) is None, f"scoped target remains mounted: {item['target']}")
        except (OSError, ExecutionError) as exc:
            failures.append(str(exc))
    for item in transaction["preserved_objects"]:
        try:
            path = context.absolute(item["source_path"])
            if item["kind"] == "file":
                require(digest_file(path, "restored CIFS record") == item["sha256"], f"original CIFS record mismatch: {path}")
            else:
                directory_lstat(path, "restored CIFS directory")
        except (OSError, ExecutionError) as exc:
            failures.append(str(exc))
    try:
        parent_mount(context)
        require(digest_file(context.absolute("/etc/fstab"), "fstab") == pre_state["fstab"]["sha256"], "fstab changed during rollback")
        require(docker_snapshot(context) == pre_state["docker"], "Docker changed during rollback")
        assert_live_k21d_absent(context)
    except (OSError, ExecutionError) as exc:
        failures.append(str(exc))

    return {
        "stopped_units": stopped,
        "disabled_units": disabled,
        "removed_unit_files": removed,
        "nfs_objects_retained": True,
        "backup_retained": True,
        "parent_collective_unchanged": not failures,
        "docker_restart_performed": False,
        "k21d_installation_performed": False,
        "failures": failures,
        "succeeded": not failures,
    }


def build_success_receipt(
    context: ExecutionContext,
    transaction: dict[str, Any],
    transaction_sha256: str,
    backup_record: dict[str, Any],
    nfs_report: dict[str, Any],
    verification: dict[str, Any],
) -> dict[str, Any]:
    operator = transaction["operator_authorization"]
    return {
        "schema": RECEIPT_SCHEMA,
        "transaction_id": transaction["transaction_id"],
        "transaction_sha256": transaction_sha256,
        "authorization_id": operator["authorization_id"],
        "authorization_sha256": operator["record_sha256"],
        "repository_head": transaction["repository_head"],
        "completed_at": utc_text(context.now()),
        "backup": backup_record,
        "nfs_preparation": nfs_report,
        "verification": verification,
        "authorization_consumed": True,
        "parent_collective_change_performed": False,
        "fstab_modified": False,
        "docker_restarted": False,
        "k21d_installation_performed": False,
        "k21d_activation_performed": False,
        "execution_allowed": False,
        "mutation_authority": False,
        "outcome": "SCOPED_NFS_STORAGE_ACTIVE",
    }


def build_failure_receipt(
    context: ExecutionContext,
    transaction: dict[str, Any],
    transaction_sha256: str,
    backup_record: dict[str, Any],
    consumption_written: bool,
    runtime: dict[str, Any],
    rollback: dict[str, Any] | None,
    failure: BaseException,
) -> dict[str, Any]:
    operator = transaction["operator_authorization"]
    return {
        "schema": RECEIPT_SCHEMA,
        "transaction_id": transaction["transaction_id"],
        "transaction_sha256": transaction_sha256,
        "authorization_id": operator["authorization_id"],
        "authorization_sha256": operator["record_sha256"],
        "repository_head": transaction["repository_head"],
        "failed_at": utc_text(context.now()),
        "failure": f"{type(failure).__name__}: {failure}",
        "backup": backup_record,
        "authorization_consumed": consumption_written,
        "nfs_objects_may_have_been_created": runtime["nfs_preparation_attempted"],
        "rollback": rollback,
        "parent_collective_change_performed": False,
        "fstab_modified": False,
        "docker_restarted": False,
        "k21d_installation_performed": False,
        "k21d_activation_performed": False,
        "execution_allowed": False,
        "mutation_authority": False,
        "outcome": (
            "PREMUTATION_FAILURE_BACKUP_RETAINED"
            if not consumption_written
            else (
                "ROLLED_BACK_SCOPED_UNITS_NFS_COPIES_RETAINED"
                if rollback is not None and rollback.get("succeeded")
                else "ROLLBACK_INCOMPLETE_OPERATOR_INSPECTION_REQUIRED"
            )
        ),
    }


def execute_transaction(
    context: ExecutionContext,
    transaction_path: Path,
) -> dict[str, Any]:
    context.repository = context.repository.resolve()
    transaction_path = transaction_path.resolve()
    transaction = read_json(transaction_path, "storage transaction")
    transaction_id = transaction.get("transaction_id")
    require(isinstance(transaction_id, str), "transaction ID missing")
    require(transaction_path == logical_transaction_path(context.repository, transaction_id), "transaction path is not canonical")
    transaction_sha256 = digest_file(transaction_path, "storage transaction")
    validate_repository(context, transaction["repository_head"])
    validate_live_dependencies(context)
    validate_transaction(context, transaction)

    operator = transaction["operator_authorization"]
    authorization_path = (context.repository / operator["record_path"]).resolve()
    require(authorization_path == context.repository / operator["record_path"], "authorization path traverses a symlink")
    require(digest_file(authorization_path, "storage authorization") == operator["record_sha256"], "authorization digest mismatch")

    consumption_path, receipt_path = record_paths(context, transaction_id)
    assert_absent(consumption_path, "authorization consumption")
    assert_absent(receipt_path, "storage receipt")
    backup_directory = context.absolute(transaction["backup"]["root"]) / transaction["backup"]["backup_id"]
    binding_path = context.absolute(transaction["backup"]["root"]) / f"{transaction['backup']['binding_id']}.json"
    assert_absent(backup_directory, "transaction backup")
    assert_absent(binding_path, "backup binding")

    lock_path = context.absolute(LOCK_PATH)
    secure_makedirs(lock_path.parent, 0o755)
    lock_descriptor = os.open(
        lock_path,
        os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0),
        0o600,
    )
    backup_record: dict[str, Any] | None = None
    pre_state: dict[str, Any] | None = None
    consumption_written = False
    runtime: dict[str, Any] = {
        "installed_units": [],
        "enabled_units": [],
        "started_units": [],
        "daemon_reload_performed": False,
        "nfs_preparation_attempted": False,
        "nfs_prepared": False,
    }
    try:
        try:
            fcntl.flock(lock_descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ExecutionError("another K21D storage transaction holds the lock") from exc

        validate_repository(context, transaction["repository_head"])
        validate_live_dependencies(context)
        require(digest_file(transaction_path, "storage transaction") == transaction_sha256, "transaction changed while waiting for lock")
        validate_transaction(context, transaction)
        assert_absent(consumption_path, "authorization consumption")
        assert_absent(receipt_path, "storage receipt")
        assert_absent(backup_directory, "transaction backup")
        assert_absent(binding_path, "backup binding")
        pre_state = validate_initial_state(context, transaction)

        backup_record = create_verified_backup(
            context,
            transaction,
            transaction_path,
            transaction_sha256,
            authorization_path,
            pre_state,
        )
        validate_backup_readback(backup_record)

        secure_makedirs(consumption_path.parent)
        consumption = build_consumption(
            context,
            transaction,
            transaction_sha256,
            backup_record,
        )
        write_json_exclusive(consumption_path, consumption)
        consumption_written = True
        validate_consumption(consumption_path, transaction, transaction_sha256)

        runtime["nfs_preparation_attempted"] = True
        nfs_report = prepare_nfs(
            context,
            transaction,
            transaction_path,
            transaction_sha256,
        )
        runtime["nfs_prepared"] = True
        require(len(nfs_report.get("objects", [])) == 3, "NFS preparation object count mismatch")
        install_units(context, transaction, runtime)
        verification = verify_post_state(context, transaction, pre_state)
        validate_backup_readback(backup_record)
        validate_consumption(consumption_path, transaction, transaction_sha256)

        receipt = build_success_receipt(
            context,
            transaction,
            transaction_sha256,
            backup_record,
            nfs_report,
            verification,
        )
        write_json_exclusive(receipt_path, receipt)
        require(read_json(receipt_path, "storage receipt") == receipt, "storage receipt readback mismatch")
        return receipt
    except BaseException as exc:
        if os.path.lexists(consumption_path):
            consumption_written = True
        rollback: dict[str, Any] | None = None
        if consumption_written and pre_state is not None:
            try:
                rollback = rollback_units(context, transaction, runtime, pre_state)
            except BaseException as rollback_exc:
                rollback = {
                    "succeeded": False,
                    "failures": [f"{type(rollback_exc).__name__}: {rollback_exc}"],
                    "nfs_objects_retained": True,
                    "backup_retained": True,
                    "docker_restart_performed": False,
                    "k21d_installation_performed": False,
                }
        if backup_record is not None and not os.path.lexists(receipt_path):
            try:
                secure_makedirs(receipt_path.parent)
                failure_receipt = build_failure_receipt(
                    context,
                    transaction,
                    transaction_sha256,
                    backup_record,
                    consumption_written,
                    runtime,
                    rollback,
                    exc,
                )
                write_json_exclusive(receipt_path, failure_receipt)
            except BaseException as journal_exc:
                raise ExecutionError(
                    f"{exc}; failure receipt error: {journal_exc}; rollback={rollback}"
                ) from journal_exc
        if isinstance(exc, ExecutionError):
            raise ExecutionError(f"{exc}; rollback={rollback}") from exc
        raise ExecutionError(f"{type(exc).__name__}: {exc}; rollback={rollback}") from exc
    finally:
        try:
            fcntl.flock(lock_descriptor, fcntl.LOCK_UN)
        finally:
            os.close(lock_descriptor)


def offline_self_test() -> None:
    require(len(LIVE_K21D_PATHS) == 8, "live path set changed")
    require(PARENT_SOURCE == "//unimatrix6/docker", "parent source changed")
    require(PARENT_FSTYPE == "cifs", "parent filesystem changed")
    require(NFS_EXPORT_ROOT == "192.168.50.10:/volume1/spotvault", "NFS export changed")
    require("soft" not in NFS_MOUNT_OPTIONS.split(","), "soft NFS option prohibited")
    require("hard" in NFS_MOUNT_OPTIONS.split(","), "hard NFS option missing")


def build_live_context(repository: Path) -> ExecutionContext:
    return ExecutionContext(
        repository=repository,
        system_root=Path("/"),
        command_runner=default_runner,
        now=lambda: datetime.now(timezone.utc),
        live=True,
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Post-2.39 K21D separately authorized scoped NFS storage executor"
    )
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--offline-self-test", action="store_true")
    action.add_argument("--execute", action="store_true")
    action.add_argument("--internal-prepare-nfs", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--transaction", type=Path)
    parser.add_argument("--transaction-sha256")
    parser.add_argument("--consumption", type=Path)
    parser.add_argument("--repository", type=Path, default=LIVE_REPOSITORY)
    args = parser.parse_args()

    if args.offline_self_test:
        offline_self_test()
        print("[PASS] K21D scoped NFS storage executor offline self-test")
        print("storage_mutation_performed=false")
        print("daemon_reload_performed=false")
        print("docker_restarted=false")
        print("k21d_installation_performed=false")
        print("execution_allowed=false")
        print("mutation_authority=false")
        return 0

    context = build_live_context(args.repository.resolve())
    if args.internal_prepare_nfs:
        require(args.transaction is not None, "internal preparation requires --transaction")
        require(args.transaction_sha256 is not None, "internal preparation requires --transaction-sha256")
        require(args.consumption is not None, "internal preparation requires --consumption")
        transaction_path = args.transaction.resolve()
        transaction = read_json(transaction_path, "storage transaction")
        report = prepare_nfs_in_private_namespace(
            context,
            transaction,
            transaction_path,
            args.transaction_sha256,
            args.consumption.resolve(),
        )
        print(json.dumps(report, sort_keys=True))
        return 0

    require(args.transaction is not None, "--execute requires --transaction")
    require(args.transaction_sha256 is None, "--transaction-sha256 is internal-only")
    require(args.consumption is None, "--consumption is internal-only")
    try:
        receipt = execute_transaction(context, args.transaction)
    except (OSError, ExecutionError) as exc:
        print(f"[DENY] K21D scoped NFS storage transaction failed closed: {exc}", file=sys.stderr)
        print("parent_collective_change_performed=false", file=sys.stderr)
        print("docker_restarted=false", file=sys.stderr)
        print("k21d_installation_performed=false", file=sys.stderr)
        print("k21d_activation_performed=false", file=sys.stderr)
        print("execution_allowed=false", file=sys.stderr)
        print("mutation_authority=false", file=sys.stderr)
        return 2

    print("[PASS] K21D scoped NFS storage transaction complete")
    print(f"transaction_id={receipt['transaction_id']}")
    print("scoped_nfs_mounts_active=true")
    print("parent_collective_change_performed=false")
    print("docker_restarted=false")
    print("k21d_installation_performed=false")
    print("k21d_activation_performed=false")
    print("execution_allowed=false")
    print("mutation_authority=false")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ExecutionError as exc:
        print(f"[DENY] {exc}", file=sys.stderr)
        raise SystemExit(2)
