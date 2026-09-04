#!/usr/bin/env python3
"""Offline successful-execution tests for the K21D storage executor."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import shutil
import stat
import sys
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence


HERE = Path(__file__).resolve().parent
EXECUTOR = HERE / "post239-k21d-scoped-nfs-storage.py"
NOW = datetime(2026, 9, 3, 12, 0, 0, tzinfo=timezone.utc)
HEAD = "1" * 40


def load_executor() -> Any:
    spec = importlib.util.spec_from_file_location("k21d_storage_executor", EXECUTOR)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load executor")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha_file(path: Path) -> str:
    return sha_bytes(path.read_bytes())


def write(path: Path, data: bytes, mode: int = 0o600) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    path.chmod(mode)


@dataclass
class FakeCommands:
    module: Any
    mounts: dict[str, tuple[str, str, str]]
    active: set[str] = field(default_factory=set)
    enabled: set[str] = field(default_factory=set)
    calls: list[tuple[str, ...]] = field(default_factory=list)
    fail_start_unit: str | None = None
    tamper_path_on_start_failure: Path | None = None
    docker_pid: str = "4242"
    docker_entered: str = "987654321"

    def __call__(
        self,
        arguments: Sequence[str],
        _cwd: Path | None,
    ) -> Any:
        command = tuple(str(value) for value in arguments)
        command = (Path(command[0]).name, *command[1:])
        self.calls.append(command)
        if command[:4] == ("findmnt", "-rn", "-T", "/mnt/collective"):
            return self.module.CommandResult(
                0,
                "systemd-1 autofs\n//unimatrix6/docker cifs\n",
                "",
            )
        if command[:3] == ("findmnt", "-rn", "-M"):
            target = command[3]
            for unit, (source, mount_target, options) in self.mounts.items():
                if target == mount_target and unit in self.active:
                    return self.module.CommandResult(
                        0,
                        f"{source} nfs4 {options}\n",
                        "",
                    )
            return self.module.CommandResult(1, "", "not mounted")
        if command == ("systemctl", "is-active", "docker.service"):
            return self.module.CommandResult(0, "active\n", "")
        if command == (
            "systemctl",
            "show",
            "docker.service",
            "-p",
            "MainPID",
            "--value",
        ):
            return self.module.CommandResult(0, self.docker_pid + "\n", "")
        if command == (
            "systemctl",
            "show",
            "docker.service",
            "-p",
            "ActiveEnterTimestampMonotonic",
            "--value",
        ):
            return self.module.CommandResult(0, self.docker_entered + "\n", "")
        if len(command) == 3 and command[:2] == ("systemctl", "is-active"):
            state = "active" if command[2] in self.active else "inactive"
            return self.module.CommandResult(0 if state == "active" else 3, state + "\n", "")
        if len(command) == 3 and command[:2] == ("systemctl", "is-enabled"):
            state = "enabled" if command[2] in self.enabled else "disabled"
            return self.module.CommandResult(0 if state == "enabled" else 1, state + "\n", "")
        if command == ("systemctl", "daemon-reload"):
            return self.module.CommandResult(0, "", "")
        if len(command) == 3 and command[:2] == ("systemctl", "enable"):
            self.enabled.add(command[2])
            return self.module.CommandResult(0, "", "")
        if len(command) == 3 and command[:2] == ("systemctl", "disable"):
            self.enabled.discard(command[2])
            return self.module.CommandResult(0, "", "")
        if len(command) == 3 and command[:2] == ("systemctl", "start"):
            if command[2] == self.fail_start_unit:
                if self.tamper_path_on_start_failure is not None:
                    self.tamper_path_on_start_failure.write_text(
                        "operator change during transaction\n",
                        encoding="utf-8",
                    )
                return self.module.CommandResult(1, "", "injected start failure")
            self.active.add(command[2])
            return self.module.CommandResult(0, "", "")
        if len(command) == 3 and command[:2] == ("systemctl", "stop"):
            self.active.discard(command[2])
            return self.module.CommandResult(0, "", "")
        return self.module.CommandResult(99, "", f"unexpected command: {command}")


@dataclass
class Fixture:
    module: Any
    root: Path
    repository: Path
    system_root: Path
    nfs_root: Path
    transaction: dict[str, Any]
    transaction_path: Path
    authorization_path: Path
    runner: FakeCommands
    context: Any
    original_manifest: bytes
    original_transaction: bytes


def build_fixture(module: Any, root: Path) -> Fixture:
    repository = root / "repository"
    system_root = root / "system"
    nfs_root = root / "nfs"
    (repository / "watch/storage").mkdir(parents=True)
    (repository / "watch/review/bundles").mkdir(parents=True)
    nfs_root.mkdir()

    for name in ("post239-k21d-backup.mount", "post239-k21d-evidence.mount"):
        shutil.copy2(HERE / name, repository / "watch/storage" / name)

    write(system_root / "etc/fstab", b"//unimatrix6/docker /mnt/collective cifs defaults 0 0\n", 0o644)
    original_manifest = b'{"original":"backup-manifest"}\n'
    original_transaction = b'{"original":"revoked-transaction"}\n'
    backup_source = system_root / "mnt/collective/backups/spot-core/post239-k21d"
    evidence_source = system_root / "mnt/collective/logs/spot/actions/post239-k21d"
    write(
        backup_source / "BACKUP-POST239-K21D-20260902T135309Z.json",
        original_manifest,
        0o555,
    )
    (backup_source / "BACKUP-POST239-K21D-20260902T135309Z-files").mkdir()
    write(
        evidence_source / "INSTALL-POST239-K21D-20260902T135309Z.json",
        original_transaction,
        0o555,
    )

    authorization_id = "AUTH-STORAGE-POST239-K21D-20260903T120000Z"
    transaction_id = "STORAGE-POST239-K21D-20260903T120000Z"
    authorization_path = repository / "watch/review/bundles" / f"{authorization_id}.json"
    authorization = {"authorization_id": authorization_id, "transaction_id": transaction_id}
    write(
        authorization_path,
        (json.dumps(authorization, sort_keys=True) + "\n").encode(),
    )

    mounts: list[dict[str, Any]] = []
    mount_definitions = (
        (
            "backup",
            "192.168.50.10:/volume1/spotvault/backups/spot-core/post239-k21d",
            "/mnt/collective/backups/spot-core/post239-k21d",
            "mnt-collective-backups-spot\\x2dcore-post239\\x2dk21d.mount",
            "post239-k21d-backup.mount",
        ),
        (
            "evidence",
            "192.168.50.10:/volume1/spotvault/logs/spot/actions/post239-k21d",
            "/mnt/collective/logs/spot/actions/post239-k21d",
            "mnt-collective-logs-spot-actions-post239\\x2dk21d.mount",
            "post239-k21d-evidence.mount",
        ),
    )
    mount_map: dict[str, tuple[str, str, str]] = {}
    effective_options = ",".join(sorted(module.REQUIRED_EFFECTIVE_NFS_OPTIONS))
    for purpose, source, target, unit_name, template_name in mount_definitions:
        template_path = f"watch/storage/{template_name}"
        entry = {
            "purpose": purpose,
            "source": source,
            "target": target,
            "unit_name": unit_name,
            "template_path": template_path,
            "template_sha256": sha_file(repository / template_path),
            "installed_path": f"/etc/systemd/system/{unit_name}",
            "active_before": False,
            "enabled_before": False,
        }
        mounts.append(entry)
        mount_map[unit_name] = (source, target, effective_options)

    preserved_objects = [
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
            "sha256": sha_bytes(original_manifest),
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
            "sha256": sha_bytes(original_transaction),
            "mode": "0400",
            "uid": 0,
            "gid": 0,
        },
    ]

    transaction = {
        "schema": "offline.fixture",
        "transaction_id": transaction_id,
        "generated_at": "2026-09-03T11:55:00Z",
        "expires_at": "2026-09-03T13:00:00Z",
        "host": "spot-core",
        "repository_head": HEAD,
        "design_review": {},
        "implementation_review": {},
        "implementation": [],
        "operator_authorization": {
            "authorization_id": authorization_id,
            "record_path": f"watch/review/bundles/{authorization_id}.json",
            "record_sha256": sha_file(authorization_path),
            "single_use": True,
            "consumed": False,
        },
        "backup": {
            "backup_id": "BACKUP-STORAGE-POST239-K21D-20260903T120000Z",
            "root": str(module.BACKUP_BASE),
            "binding_id": "BACKUP-BINDING-STORAGE-POST239-K21D-20260903T120000Z",
            "create_before_mutation": True,
            "verified_before_mutation": True,
        },
        "rollback": {},
        "mounts": mounts,
        "preserved_objects": preserved_objects,
        "governance": {},
        "status": "offline.fixture",
    }
    transaction_path = repository / "watch/review/bundles" / f"{transaction_id}.json"
    write(
        transaction_path,
        (json.dumps(transaction, indent=2, sort_keys=True) + "\n").encode(),
    )

    runner = FakeCommands(module, mount_map)

    def resolve(logical: Path) -> Path:
        for unit, (source, target_text, _options) in mount_map.items():
            target = Path(target_text)
            try:
                relative = logical.relative_to(target)
            except ValueError:
                continue
            if unit in runner.active:
                export_relative = source.split("/volume1/spotvault/", 1)[1]
                nfs_target = nfs_root / export_relative
                return nfs_target / relative
        return system_root / logical.relative_to("/")

    def prepare_nfs(
        context: Any,
        payload: dict[str, Any],
        _transaction_path: Path,
        _transaction_sha: str,
    ) -> dict[str, Any]:
        objects = []
        for item in payload["preserved_objects"]:
            objects.append(module.create_nfs_object(context, nfs_root, item))
        return {
            "source": module.NFS_EXPORT_ROOT,
            "objects": objects,
            "temporary_mount_removed": True,
            "persistent_probe_artifact": False,
        }

    context = module.ExecutionContext(
        repository=repository,
        system_root=system_root,
        command_runner=runner,
        now=lambda: NOW,
        live=False,
        path_resolver=resolve,
        nfs_preparer=prepare_nfs,
        validation_hook=lambda _payload, _repository, _now: None,
    )
    return Fixture(
        module,
        root,
        repository,
        system_root,
        nfs_root,
        transaction,
        transaction_path,
        authorization_path,
        runner,
        context,
        original_manifest,
        original_transaction,
    )


def assert_metadata(path: Path, mode: int) -> None:
    info = path.lstat()
    assert stat.S_IMODE(info.st_mode) == mode, (path, oct(stat.S_IMODE(info.st_mode)))
    assert info.st_uid == 0 and info.st_gid == 0, (path, info.st_uid, info.st_gid)


def test_success(module: Any) -> None:
    with tempfile.TemporaryDirectory(prefix="k21d-storage-success.") as temporary:
        fixture = build_fixture(module, Path(temporary))
        receipt = module.execute_transaction(fixture.context, fixture.transaction_path)
        assert receipt["outcome"] == "SCOPED_NFS_STORAGE_ACTIVE"
        assert receipt["authorization_consumed"] is True
        assert receipt["parent_collective_change_performed"] is False
        assert receipt["docker_restarted"] is False
        assert receipt["k21d_installation_performed"] is False
        assert receipt["k21d_activation_performed"] is False
        assert receipt["execution_allowed"] is False
        assert receipt["mutation_authority"] is False

        backup_source = fixture.system_root / "mnt/collective/backups/spot-core/post239-k21d"
        evidence_source = fixture.system_root / "mnt/collective/logs/spot/actions/post239-k21d"
        assert (
            backup_source / "BACKUP-POST239-K21D-20260902T135309Z.json"
        ).read_bytes() == fixture.original_manifest
        assert (
            evidence_source / "INSTALL-POST239-K21D-20260902T135309Z.json"
        ).read_bytes() == fixture.original_transaction

        for item in fixture.transaction["preserved_objects"]:
            destination = fixture.nfs_root / item["destination_relative"]
            assert_metadata(destination, int(item["mode"], 8))
            if item["kind"] == "file":
                assert sha_file(destination) == item["sha256"]
            else:
                assert destination.is_dir() and not list(destination.iterdir())

        for item in fixture.transaction["mounts"]:
            unit_path = fixture.system_root / item["installed_path"].lstrip("/")
            assert sha_file(unit_path) == item["template_sha256"]
            assert_metadata(unit_path, 0o644)
            assert item["unit_name"] in fixture.runner.active
            assert item["unit_name"] in fixture.runner.enabled

        backup_root = fixture.system_root / str(module.BACKUP_BASE).lstrip("/")
        assert any(backup_root.rglob("*.manifest.json"))
        assert any(backup_root.glob("BACKUP-BINDING-*.json"))
        evidence_root = fixture.system_root / str(module.EVIDENCE_BASE).lstrip("/")
        consumption = evidence_root / f"{fixture.transaction['transaction_id']}.consumption.json"
        receipt_path = evidence_root / f"{fixture.transaction['transaction_id']}.receipt.json"
        assert json.loads(consumption.read_text())["single_use"] is True
        assert json.loads(receipt_path.read_text())["outcome"] == "SCOPED_NFS_STORAGE_ACTIVE"

        assert not any(
            call[:2] == ("systemctl", "restart") and "docker" in " ".join(call)
            for call in fixture.runner.calls
        )
        assert fixture.runner.calls.count(("systemctl", "daemon-reload")) == 1

        try:
            module.execute_transaction(fixture.context, fixture.transaction_path)
        except module.ExecutionError as exc:
            assert "already exists" in str(exc)
        else:
            raise AssertionError("single-use replay was accepted")


def main() -> int:
    module = load_executor()
    test_success(module)
    print("[PASS] K21D scoped NFS storage successful-execution test")
    print("success_cases=1")
    print("single_use_replay_denied=true")
    print("host_mounts_performed=false")
    print("host_systemd_modified=false")
    print("docker_restarted=false")
    print("k21d_installation_performed=false")
    print("execution_allowed=false")
    print("mutation_authority=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
