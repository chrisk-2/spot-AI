#!/usr/bin/env python3
"""Offline execution and rollback tests for the K21D live executor."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import os
import shutil
import stat
import sys
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Sequence


HERE = Path(__file__).resolve().parent
EXECUTOR = HERE / "controlled-read-observe-install-transaction.py"
VALIDATOR = HERE / "controlled-read-observe-install-transaction-validate.py"


def load_executor() -> Any:
    spec = importlib.util.spec_from_file_location("k21d_executor", EXECUTOR)
    if spec is None or spec.loader is None:
        raise AssertionError("cannot load executor")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def sha(path: Path) -> str:
    value = hashlib.sha256()
    value.update(path.read_bytes())
    return value.hexdigest()


def write_json(path: Path, payload: dict[str, Any], mode: int = 0o600) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    path.chmod(mode)


@dataclass
class FakeCommands:
    module: Any
    fail_verify_once: bool = False
    calls: list[tuple[str, ...]] = field(default_factory=list)

    def __call__(self, arguments: Sequence[str], cwd: Path | None) -> Any:
        command = tuple(arguments)
        self.calls.append(command)
        if command[:2] == ("systemctl", "is-active"):
            return self.module.CommandResult(3, "inactive\n", "")
        if command[:2] == ("systemctl", "is-enabled"):
            return self.module.CommandResult(1, "disabled\n", "")
        if command[:2] == ("systemctl", "show"):
            return self.module.CommandResult(0, "0\n", "")
        if command[:2] == ("systemctl", "list-unit-files"):
            return self.module.CommandResult(0, "", "")
        if command[:2] == ("systemctl", "list-units"):
            return self.module.CommandResult(
                0,
                "ssh.service loaded active running OpenSSH server\n",
                "",
            )
        if command == ("systemctl", "daemon-reload"):
            return self.module.CommandResult(0, "", "")
        if command[:2] == ("systemd-analyze", "verify"):
            if self.fail_verify_once:
                self.fail_verify_once = False
                return self.module.CommandResult(1, "", "injected unit verification failure")
            return self.module.CommandResult(0, "", "")
        if command and command[0] == "python3":
            return self.module.CommandResult(0, "offline PASS\n", "")
        return self.module.CommandResult(1, "", f"unexpected command: {command}")

    def count(self, *command: str) -> int:
        return sum(item == tuple(command) for item in self.calls)


class Fixture:
    def __init__(self, module: Any, *, preexisting: set[int] | None = None) -> None:
        self.module = module
        self.temp = tempfile.TemporaryDirectory(prefix="spot-k21d-live-executor-")
        self.base = Path(self.temp.name)
        self.repository = self.base / "repository"
        self.system_root = self.base / "system-root"
        self.now = datetime(2026, 8, 29, 18, 0, 0, tzinfo=timezone.utc)
        self.head = "a" * 40
        self.transaction_id = "INSTALL-POST239-K21D-OFFLINE0001"
        self.authorization_id = "AUTH-POST239-K21D-INSTALLATION-OFFLINE0001"
        self.backup_id = "BACKUP-POST239-K21D-OFFLINE0001"
        self.backup_binding = "BACKUP-BINDING-POST239-K21D-OFFLINE0001"
        self.rollback_binding = "ROLLBACK-BINDING-POST239-K21D-OFFLINE0001"
        self.preexisting = preexisting or set()
        self.command_runner = FakeCommands(module)

        (self.repository / "watch/observe").mkdir(parents=True)
        (self.repository / "watch/review/bundles").mkdir(parents=True)
        for base in (
            "/usr/local/lib/spot",
            "/etc/spot",
            "/etc/systemd/system",
            "/usr/lib/systemd/system",
            "/lib/systemd/system",
            "/run/lock",
            "/mnt/collective/logs/spot/actions/post239-k21d",
            "/mnt/collective/backups/spot-core/post239-k21d",
        ):
            self.physical(base).mkdir(parents=True, exist_ok=True)
            self.physical(base).chmod(0o755)

        shutil.copy2(VALIDATOR, self.repository / self.module.TRANSACTION_VALIDATOR)
        self._create_sources()
        self._create_references()
        self._create_destinations()
        self._create_authorization()
        self._create_backup_and_transaction()

    def close(self) -> None:
        self.temp.cleanup()

    def physical(self, absolute: str | Path) -> Path:
        return self.system_root / str(absolute).lstrip("/")

    def _create_sources(self) -> None:
        for index, (source, _destination, mode) in enumerate(self.module.FILE_MAP, start=1):
            path = self.repository / source
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(f"K21D fixture source {index}\n".encode())
            path.chmod(int(mode, 8) if index != 2 else 0o644)
        for name in (
            "controlled_read_observe_validation_v1.py",
            "controlled-read-observe-replay-bounds-validate.py",
            "controlled-read-observe-install-validate.py",
            "controlled-read-observe-install-transaction-failure-test.py",
        ):
            path = self.repository / "watch/observe" / name
            if not path.exists():
                path.write_text("raise SystemExit(0)\n", encoding="utf-8")

    def _create_references(self) -> None:
        self.review_rel = Path(
            "watch/review/bundles/POST239-K21D-BLUEPRINT-PASS-20260828T150447Z.json"
        )
        write_json(self.repository / self.review_rel, {"review": {"verdict": "PASS"}})
        self.implementation_rel = Path(
            "watch/review/bundles/POST239-K21D-IMPLEMENTATION-PASS-20260828T222053Z.json"
        )
        self.mapping_rel = Path(
            "watch/review/bundles/POST239-K21D-MAPPING-CORRECTION-PASS-20260829T162201Z.json"
        )
        self.live_rel = Path(
            "watch/review/bundles/POST239-K21D-LIVE-EXECUTOR-PASS-OFFLINE0001.json"
        )
        write_json(self.repository / self.implementation_rel, {"verdict": "PASS"})
        write_json(self.repository / self.mapping_rel, {"verdict": "PASS"})
        write_json(
            self.repository / self.live_rel,
            {
                "verdict": "PASS",
                "live_executor_accepted": True,
                "system_path_installation_authorized": False,
            },
        )
        self.rollback_rel = Path("watch/observe/controlled-read-observe-install-rollback.md")
        rollback = self.repository / self.rollback_rel
        rollback.write_text("K21D fixed eight-file rollback fixture\n", encoding="utf-8")
        rollback.chmod(0o600)

    def _create_destinations(self) -> None:
        self.original: dict[int, bytes] = {}
        for index, (_source, destination, mode) in enumerate(self.module.FILE_MAP, start=1):
            if index not in self.preexisting:
                continue
            physical = self.physical(destination)
            physical.parent.mkdir(parents=True, exist_ok=True)
            content = f"preexisting destination {index}\n".encode()
            physical.write_bytes(content)
            physical.chmod(int(mode, 8))
            self.original[index] = content

    def _mapping_records(self) -> list[dict[str, Any]]:
        result = []
        for source, destination, mode in self.module.FILE_MAP:
            result.append(
                {
                    "source": source,
                    "source_sha256": sha(self.repository / source),
                    "destination": destination,
                    "mode": mode,
                    "owner": "root",
                    "group": "root",
                }
            )
        return result

    def _create_authorization(self) -> None:
        self.authorization_rel = Path(
            f"watch/review/bundles/{self.authorization_id}.json"
        )
        self.authorization_path = self.repository / self.authorization_rel
        payload = {
            "schema": self.module.AUTH_SCHEMA,
            "authorization_id": self.authorization_id,
            "transaction_id": self.transaction_id,
            "generated_at": (self.now - timedelta(minutes=10)).isoformat(),
            "expires_at": (self.now + timedelta(hours=2)).isoformat(),
            "authorized_by": {
                "role": "operator",
                "identity": "offline-fixture",
                "authority": "single_use_installation_only",
            },
            "repository": {
                "host": "spot-core",
                "branch": "main",
                "head": self.head,
                "required_clean_except_runtime_drift": self.module.RUNTIME_DRIFT,
            },
            "correlated_reviews": {
                "blueprint_pass_path": str(self.review_rel),
                "blueprint_pass_sha256": sha(self.repository / self.review_rel),
                "implementation_pass_path": str(self.implementation_rel),
                "implementation_pass_sha256": sha(self.repository / self.implementation_rel),
                "mapping_correction_pass_path": str(self.mapping_rel),
                "mapping_correction_pass_sha256": sha(self.repository / self.mapping_rel),
                "live_executor_pass_path": str(self.live_rel),
                "live_executor_pass_sha256": sha(self.repository / self.live_rel),
                "worker05_verdict": "PASS",
            },
            "fixed_mappings": self._mapping_records(),
            "scope": {
                "k21d_transaction_authorized": True,
                "backup_creation_authorized": True,
                "installation_manifest_creation_authorized": True,
                "system_path_installation_authorized": True,
                "installation_receipt_creation_authorized": True,
                "authorization_consumption_authorized": True,
                "daemon_reload_if_unit_changed_authorized": True,
                "rollback_execution_authorized": True,
                "rollback_stop_if_unexpected_active_authorized": True,
                "unconditional_daemon_reload_authorized": False,
                "activation_authorized": False,
                "enablement_authorized": False,
                "scheduling_authorized": False,
                "request_dispatch_authorized": False,
                "production_observation_authorized": False,
                "service_action_authorized": False,
                "remediation_authorized": False,
            },
            "replay_control": {
                "single_use": True,
                "consumed": False,
                "installation_completed": False,
                "rollback_completed": False,
            },
            "governance": {
                "spot_core_sole_authority": True,
                "worker_self_apply_allowed": False,
                "live_executor_enabled": False,
                "execution_allowed": False,
                "mutation_authority": False,
            },
            "status": "AUTHORIZED_FOR_SINGLE_K21D_INSTALLATION_ONLY",
        }
        write_json(self.authorization_path, payload)

    def _create_backup_and_transaction(self) -> None:
        files = []
        backup_files = []
        backup_live_dir = self.module.BACKUP_BASE / f"{self.backup_id}-files"
        backup_physical_dir = self.physical(backup_live_dir)
        backup_physical_dir.mkdir(parents=True, exist_ok=True)
        backup_physical_dir.chmod(0o700)
        for index, (source, destination, mode) in enumerate(self.module.FILE_MAP, start=1):
            source_sha = sha(self.repository / source)
            if index in self.preexisting:
                backup_live = backup_live_dir / f"{index:02d}-{Path(destination).name}.backup"
                backup_physical = self.physical(backup_live)
                if backup_physical.exists():
                    backup_physical.unlink()
                backup_physical.write_bytes(self.original[index])
                backup_physical.chmod(0o400)
                backup_sha: str | None = sha(backup_physical)
                backup_path: str | None = str(backup_live)
                preexisting = True
                before_type = "regular"
                destination_info = self.physical(destination).stat()
                mode_before: str | None = f"{stat.S_IMODE(destination_info.st_mode):04o}"
                uid_before: int | None = destination_info.st_uid
                gid_before: int | None = destination_info.st_gid
            else:
                backup_sha = None
                backup_path = None
                preexisting = False
                before_type = "absent"
                mode_before = None
                uid_before = None
                gid_before = None
            files.append(
                {
                    "source": source,
                    "destination": destination,
                    "source_sha256": source_sha,
                    "mode": mode,
                    "owner": "root",
                    "group": "root",
                    "destination_preexisting": preexisting,
                    "destination_type_before": before_type,
                    "backup_sha256": backup_sha,
                }
            )
            backup_files.append(
                {
                    "source": source,
                    "destination": destination,
                    "destination_preexisting": preexisting,
                    "destination_type_before": before_type,
                    "backup_path": backup_path,
                    "backup_sha256": backup_sha,
                    "mode_before": mode_before,
                    "uid_before": uid_before,
                    "gid_before": gid_before,
                }
            )

        manifest = {
            "schema": self.module.BACKUP_SCHEMA,
            "manifest_id": self.backup_id,
            "generated_at": (self.now - timedelta(minutes=5)).isoformat(),
            "host": "spot-core",
            "repository_head": self.head,
            "authorization_id": self.authorization_id,
            "authorization_sha256": sha(self.authorization_path),
            "binding_id": self.backup_binding,
            "files": backup_files,
            "verified": True,
            "status": "VERIFIED_PREINSTALL_BACKUP",
        }
        self.manifest_live = self.module.BACKUP_BASE / f"{self.backup_id}.json"
        self.manifest_path = self.physical(self.manifest_live)
        write_json(self.manifest_path, manifest, 0o400)

        transaction = {
            "schema": "starfleet.post239.k21d_install_transaction.v1",
            "transaction_id": self.transaction_id,
            "generated_at": (self.now - timedelta(minutes=4)).isoformat(),
            "expires_at": (self.now + timedelta(hours=1)).isoformat(),
            "host": "spot-core",
            "repository_head": self.head,
            "design_review": {
                "record_path": str(self.review_rel),
                "record_sha256": sha(self.repository / self.review_rel),
                "verdict": "PASS",
            },
            "operator_authorization": {
                "authorization_id": self.authorization_id,
                "record_path": str(self.authorization_rel),
                "record_sha256": sha(self.authorization_path),
                "system_path_installation_authorized": True,
                "single_use": True,
                "consumed": False,
            },
            "backup": {
                "manifest_id": self.backup_id,
                "manifest_path": str(self.manifest_live),
                "manifest_sha256": sha(self.manifest_path),
                "binding_id": self.backup_binding,
                "verified": True,
            },
            "rollback": {
                "document_path": str(self.rollback_rel),
                "document_sha256": sha(self.repository / self.rollback_rel),
                "binding_id": self.rollback_binding,
                "verified": True,
            },
            "files": files,
            "planned_service_state": {
                "daemon_reload_if_unit_changed": True,
                "unconditional_daemon_reload": False,
                "service_start_planned": False,
                "service_enablement_planned": False,
                "timer_installation_planned": False,
                "request_dispatch_planned": False,
                "production_observation_planned": False,
            },
            "governance": {
                "spot_core_sole_authority": True,
                "worker_self_apply_allowed": False,
                "activation_authorized": False,
                "enablement_authorized": False,
                "scheduling_authorized": False,
                "production_observation_authorized": False,
                "service_action_authorized": False,
                "live_executor_enabled": False,
                "execution_allowed": False,
                "mutation_authority": False,
            },
            "status": "READY_FOR_SEPARATELY_AUTHORIZED_INSTALLATION_ONLY",
        }
        self.transaction_path = self.physical(self.module.EVIDENCE_BASE) / f"{self.transaction_id}.json"
        write_json(self.transaction_path, transaction)

    def context(self) -> Any:
        return self.module.ExecutionContext(
            repository=self.repository,
            system_root=self.system_root,
            lock_path=self.physical(self.module.LOCK_PATH),
            command_runner=self.command_runner,
            now=lambda: self.now,
            hostname=lambda: "spot-core",
            live=False,
        )

    def receipt_path(self) -> Path:
        return self.physical(self.module.EVIDENCE_BASE) / f"{self.transaction_id}.receipt.json"

    def consumption_path(self) -> Path:
        return self.physical(self.module.EVIDENCE_BASE) / f"{self.transaction_id}.consumption.json"


def expect_denied(label: str, action: Any, module: Any) -> None:
    try:
        action()
    except module.ExecutionError:
        print(f"[PASS] denied: {label}")
        return
    raise AssertionError(f"unsafe case accepted: {label}")


def positive_install(module: Any) -> None:
    fixture = Fixture(module)
    try:
        receipt = module.execute_transaction(fixture.context(), fixture.transaction_path)
        assert receipt["outcome"] == "INSTALLED_DORMANT"
        assert fixture.consumption_path().is_file()
        assert fixture.receipt_path().is_file()
        for source, destination, mode in module.FILE_MAP:
            installed = fixture.physical(destination)
            assert sha(installed) == sha(fixture.repository / source)
            assert stat.S_IMODE(installed.stat().st_mode) == int(mode, 8)
        assert fixture.command_runner.count("systemctl", "daemon-reload") == 1
        forbidden = {"start", "enable", "restart", "try-restart"}
        assert not any(len(call) > 1 and call[0] == "systemctl" and call[1] in forbidden for call in fixture.command_runner.calls)
        print("[PASS] positive installation confined to offline fixture")

        expect_denied(
            "same-transaction replay",
            lambda: module.execute_transaction(fixture.context(), fixture.transaction_path),
            module,
        )
    finally:
        fixture.close()


def changed_transaction_id_authorization_reuse(module: Any) -> None:
    fixture = Fixture(module)
    try:
        changed_id = "INSTALL-POST239-K21D-OFFLINE0002"
        transaction = json.loads(fixture.transaction_path.read_text(encoding="utf-8"))
        transaction["transaction_id"] = changed_id
        changed_path = fixture.physical(module.EVIDENCE_BASE) / f"{changed_id}.json"
        write_json(changed_path, transaction)

        try:
            module.execute_transaction(fixture.context(), changed_path)
        except module.ExecutionError as exc:
            assert "authorization transaction ID mismatch" in str(exc)
            print("[PASS] denied: authorization reuse under changed transaction ID")
        else:
            raise AssertionError("changed transaction ID reused one authorization")

        evidence = fixture.physical(module.EVIDENCE_BASE)
        assert not (evidence / f"{changed_id}.consumption.json").exists()
        assert not (evidence / f"{changed_id}.receipt.json").exists()
    finally:
        fixture.close()


def completed_rollback_authorization(module: Any) -> None:
    fixture = Fixture(module)
    try:
        authorization = json.loads(fixture.authorization_path.read_text(encoding="utf-8"))
        authorization["replay_control"]["rollback_completed"] = True
        write_json(fixture.authorization_path, authorization)
        authorization_sha = sha(fixture.authorization_path)

        manifest = json.loads(fixture.manifest_path.read_text(encoding="utf-8"))
        manifest["authorization_sha256"] = authorization_sha
        write_json(fixture.manifest_path, manifest, 0o400)

        transaction = json.loads(fixture.transaction_path.read_text(encoding="utf-8"))
        transaction["operator_authorization"]["record_sha256"] = authorization_sha
        transaction["backup"]["manifest_sha256"] = sha(fixture.manifest_path)
        write_json(fixture.transaction_path, transaction)

        try:
            module.execute_transaction(fixture.context(), fixture.transaction_path)
        except module.ExecutionError as exc:
            assert "authorization rollback already completed" in str(exc)
            print("[PASS] denied: authorization with completed rollback")
        else:
            raise AssertionError("completed rollback authorization was accepted")

        assert not fixture.consumption_path().exists()
        assert not fixture.receipt_path().exists()
    finally:
        fixture.close()


def source_tamper(module: Any) -> None:
    fixture = Fixture(module)
    try:
        source = fixture.repository / module.FILE_MAP[0][0]
        source.write_text("tampered\n", encoding="utf-8")
        expect_denied(
            "source digest tamper",
            lambda: module.execute_transaction(fixture.context(), fixture.transaction_path),
            module,
        )
        assert not fixture.consumption_path().exists()
    finally:
        fixture.close()


def backup_tamper(module: Any) -> None:
    fixture = Fixture(module, preexisting={1})
    try:
        manifest = json.loads(fixture.manifest_path.read_text(encoding="utf-8"))
        backup_path = fixture.physical(manifest["files"][0]["backup_path"])
        backup_path.chmod(0o600)
        backup_path.write_text("tampered backup\n", encoding="utf-8")
        expect_denied(
            "backup content tamper",
            lambda: module.execute_transaction(fixture.context(), fixture.transaction_path),
            module,
        )
        assert fixture.physical(module.FILE_MAP[0][1]).read_bytes() == fixture.original[1]
        assert not fixture.consumption_path().exists()
    finally:
        fixture.close()


def symlink_destination(module: Any) -> None:
    fixture = Fixture(module)
    try:
        target = fixture.base / "outside-target"
        target.write_text("do not alter\n", encoding="utf-8")
        destination = fixture.physical(module.FILE_MAP[0][1])
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.symlink_to(target)
        expect_denied(
            "destination symlink",
            lambda: module.execute_transaction(fixture.context(), fixture.transaction_path),
            module,
        )
        assert target.read_text(encoding="utf-8") == "do not alter\n"
        assert not fixture.consumption_path().exists()
    finally:
        fixture.close()


def rollback_after_failure(module: Any) -> None:
    fixture = Fixture(module, preexisting={1, 8})
    try:
        fixture.command_runner.fail_verify_once = True
        expect_denied(
            "post-install failure triggers rollback",
            lambda: module.execute_transaction(fixture.context(), fixture.transaction_path),
            module,
        )
        for index, (_source, destination, _mode) in enumerate(module.FILE_MAP, start=1):
            physical = fixture.physical(destination)
            if index in fixture.preexisting:
                assert physical.read_bytes() == fixture.original[index]
            else:
                assert not os.path.lexists(physical)
        receipt = json.loads(fixture.receipt_path().read_text(encoding="utf-8"))
        assert receipt["outcome"] == "ROLLED_BACK"
        assert receipt["rollback"]["succeeded"] is True
        assert fixture.consumption_path().is_file()
        assert fixture.command_runner.count("systemctl", "daemon-reload") == 2
        print("[PASS] verified rollback restores exact pre-install state")
    finally:
        fixture.close()


def unchanged_unit_no_reload(module: Any) -> None:
    fixture = Fixture(module, preexisting={8})
    try:
        unit_source = fixture.repository / module.FILE_MAP[7][0]
        unit_destination = fixture.physical(module.FILE_MAP[7][1])
        unit_destination.write_bytes(unit_source.read_bytes())
        unit_destination.chmod(0o644)
        fixture.original[8] = unit_source.read_bytes()
        fixture._create_backup_and_transaction()
        module.execute_transaction(fixture.context(), fixture.transaction_path)
        assert fixture.command_runner.count("systemctl", "daemon-reload") == 0
        print("[PASS] daemon-reload omitted when unit content is unchanged")
    finally:
        fixture.close()


def expired_authorization(module: Any) -> None:
    fixture = Fixture(module)
    try:
        authorization = json.loads(fixture.authorization_path.read_text(encoding="utf-8"))
        authorization["expires_at"] = (fixture.now - timedelta(seconds=1)).isoformat()
        write_json(fixture.authorization_path, authorization)
        transaction = json.loads(fixture.transaction_path.read_text(encoding="utf-8"))
        transaction["operator_authorization"]["record_sha256"] = sha(fixture.authorization_path)
        transaction["expires_at"] = (fixture.now - timedelta(seconds=1)).isoformat()
        write_json(fixture.transaction_path, transaction)
        expect_denied(
            "expired authorization",
            lambda: module.execute_transaction(fixture.context(), fixture.transaction_path),
            module,
        )
    finally:
        fixture.close()


def revoked_authorization(module: Any) -> None:
    fixture = Fixture(module)
    try:
        revocation = {
            "schema": "starfleet.post239.k21d_installation_authorization_revocation.v1",
            "revoked_authorization_path": str(fixture.authorization_rel),
            "revoked_authorization_sha256": sha(fixture.authorization_path),
            "status": "REVOKED_BEFORE_USE",
        }
        path = fixture.repository / "watch/review/bundles/REVOKE-POST239-K21D-INSTALLATION-OFFLINE0001.json"
        write_json(path, revocation)
        expect_denied(
            "revoked authorization",
            lambda: module.execute_transaction(fixture.context(), fixture.transaction_path),
            module,
        )
    finally:
        fixture.close()


def receipt_collision(module: Any) -> None:
    fixture = Fixture(module)
    try:
        fixture.receipt_path().write_text("existing immutable receipt\n", encoding="utf-8")
        expect_denied(
            "receipt collision",
            lambda: module.execute_transaction(fixture.context(), fixture.transaction_path),
            module,
        )
        assert not fixture.consumption_path().exists()
    finally:
        fixture.close()


def main() -> int:
    module = load_executor()
    module.offline_self_test()
    positive_install(module)
    changed_transaction_id_authorization_reuse(module)
    completed_rollback_authorization(module)
    source_tamper(module)
    backup_tamper(module)
    symlink_destination(module)
    rollback_after_failure(module)
    unchanged_unit_no_reload(module)
    expired_authorization(module)
    revoked_authorization(module)
    receipt_collision(module)
    print("positive_tests=3")
    print("negative_tests=9")
    print("live_system_paths_touched=false")
    print("installation_performed=false")
    print("daemon_reload_performed=false")
    print("activation_authorized=false")
    print("execution_allowed=false")
    print("mutation_authority=false")
    print("RESULT: POST-2.39 K21D LIVE EXECUTOR OFFLINE TEST PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
