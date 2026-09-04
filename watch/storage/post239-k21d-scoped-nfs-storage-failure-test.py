#!/usr/bin/env python3
"""Offline denial and rollback tests for the K21D storage transaction."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
EXECUTION_TEST = HERE / "post239-k21d-scoped-nfs-storage-execution-test.py"
VALIDATOR = HERE / "post239-k21d-scoped-nfs-storage-validate.py"
NOW = datetime(2026, 9, 3, 12, 0, 0, tzinfo=timezone.utc)


def load(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def expect_execution_denial(module: Any, operation: Any, fragment: str) -> str:
    try:
        operation()
    except module.ExecutionError as exc:
        message = str(exc)
        assert fragment in message, (fragment, message)
        return message
    raise AssertionError(f"expected execution denial containing {fragment!r}")


def expect_validation_denial(module: Any, operation: Any, fragment: str) -> str:
    try:
        operation()
    except module.TransactionError as exc:
        message = str(exc)
        assert fragment in message, (fragment, message)
        return message
    raise AssertionError(f"expected validation denial containing {fragment!r}")


def receipt_path(fixture: Any) -> Path:
    return (
        fixture.system_root
        / "mnt/collective/logs/spot/actions/post239-k21d-storage"
        / f"{fixture.transaction['transaction_id']}.receipt.json"
    )


def consumption_path(fixture: Any) -> Path:
    return (
        fixture.system_root
        / "mnt/collective/logs/spot/actions/post239-k21d-storage"
        / f"{fixture.transaction['transaction_id']}.consumption.json"
    )


def assert_no_docker_restart(fixture: Any) -> None:
    assert not any(
        call[:2] in (("systemctl", "restart"), ("systemctl", "stop"))
        and "docker.service" in call
        for call in fixture.runner.calls
    )


def test_start_failure_rolls_back(execution: Any, module: Any) -> None:
    with tempfile.TemporaryDirectory(prefix="k21d-storage-start-failure.") as temporary:
        fixture = execution.build_fixture(module, Path(temporary))
        fixture.runner.fail_start_unit = fixture.transaction["mounts"][1]["unit_name"]
        expect_execution_denial(
            module,
            lambda: module.execute_transaction(fixture.context, fixture.transaction_path),
            "injected start failure",
        )
        assert not fixture.runner.active
        assert not fixture.runner.enabled
        for item in fixture.transaction["mounts"]:
            installed = fixture.system_root / item["installed_path"].lstrip("/")
            assert not installed.exists()
        failure = json.loads(receipt_path(fixture).read_text())
        assert failure["outcome"] == "ROLLED_BACK_SCOPED_UNITS_NFS_COPIES_RETAINED"
        assert failure["rollback"]["succeeded"] is True
        assert failure["authorization_consumed"] is True
        assert failure["nfs_objects_may_have_been_created"] is True
        assert consumption_path(fixture).exists()
        assert fixture.nfs_root.joinpath(
            fixture.transaction["preserved_objects"][0]["destination_relative"]
        ).exists()
        assert fixture.runner.calls.count(("systemctl", "daemon-reload")) == 2
        assert_no_docker_restart(fixture)


def test_replay_collision_denied_before_backup(execution: Any, module: Any) -> None:
    with tempfile.TemporaryDirectory(prefix="k21d-storage-replay.") as temporary:
        fixture = execution.build_fixture(module, Path(temporary))
        collision = consumption_path(fixture)
        collision.parent.mkdir(parents=True)
        collision.write_text("{}\n", encoding="utf-8")
        expect_execution_denial(
            module,
            lambda: module.execute_transaction(fixture.context, fixture.transaction_path),
            "already exists",
        )
        backup_base = fixture.system_root / str(module.BACKUP_BASE).lstrip("/")
        assert not backup_base.exists()
        assert not receipt_path(fixture).exists()
        assert not fixture.runner.calls


def test_nfs_collision_fails_closed(execution: Any, module: Any) -> None:
    with tempfile.TemporaryDirectory(prefix="k21d-storage-nfs-collision.") as temporary:
        fixture = execution.build_fixture(module, Path(temporary))
        first = fixture.transaction["preserved_objects"][0]
        collision = fixture.nfs_root / first["destination_relative"]
        collision.parent.mkdir(parents=True)
        collision.write_bytes(b"preexisting remote object\n")
        expect_execution_denial(
            module,
            lambda: module.execute_transaction(fixture.context, fixture.transaction_path),
            "NFS destination already exists",
        )
        assert collision.read_bytes() == b"preexisting remote object\n"
        assert not fixture.runner.active
        assert not fixture.runner.enabled
        failure = json.loads(receipt_path(fixture).read_text())
        assert failure["outcome"] == "ROLLED_BACK_SCOPED_UNITS_NFS_COPIES_RETAINED"
        assert failure["nfs_objects_may_have_been_created"] is True
        assert failure["rollback"]["succeeded"] is True
        assert consumption_path(fixture).exists()
        assert_no_docker_restart(fixture)


def test_changed_unit_is_retained(execution: Any, module: Any) -> None:
    with tempfile.TemporaryDirectory(prefix="k21d-storage-unit-change.") as temporary:
        fixture = execution.build_fixture(module, Path(temporary))
        second = fixture.transaction["mounts"][1]
        first = fixture.transaction["mounts"][0]
        fixture.runner.fail_start_unit = second["unit_name"]
        changed = fixture.system_root / first["installed_path"].lstrip("/")
        fixture.runner.tamper_path_on_start_failure = changed
        expect_execution_denial(
            module,
            lambda: module.execute_transaction(fixture.context, fixture.transaction_path),
            "rollback",
        )
        assert changed.exists()
        assert changed.read_text() == "operator change during transaction\n"
        unchanged = fixture.system_root / second["installed_path"].lstrip("/")
        assert not unchanged.exists()
        failure = json.loads(receipt_path(fixture).read_text())
        assert failure["outcome"] == "ROLLBACK_INCOMPLETE_OPERATOR_INSPECTION_REQUIRED"
        assert failure["rollback"]["succeeded"] is False
        assert any("refuses changed unit" in item for item in failure["rollback"]["failures"])
        assert not fixture.runner.active
        assert not fixture.runner.enabled
        assert_no_docker_restart(fixture)


def valid_contract(validator: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    implementation_sha = {
        path: hashlib.sha256(path.encode()).hexdigest()
        for path in validator.IMPLEMENTATION_PATHS
    }
    implementation_review_id = (
        "REVIEW-POST239-K21D-SCOPED-NFS-STORAGE-IMPLEMENTATION-"
        "20260903T120000Z"
    )
    implementation_review = {
        "bundle_path": f"watch/review/bundles/{implementation_review_id}.md",
        "bundle_sha256": "2" * 64,
        "result_path": (
            f"watch/review/bundles/{implementation_review_id}.worker05.json"
        ),
        "result_sha256": "3" * 64,
        "review_id": implementation_review_id,
        "reviewer": "spot-worker-05",
        "model": "deepseek-r1:32b",
        "verdict": "PASS",
    }
    authorization_id = "AUTH-STORAGE-POST239-K21D-20260903T120000Z"
    transaction_id = "STORAGE-POST239-K21D-20260903T120000Z"
    mounts = []
    for expected in validator.MOUNTS:
        mounts.append(
            {
                **expected,
                "template_sha256": implementation_sha[expected["template_path"]],
                "active_before": False,
                "enabled_before": False,
            }
        )
    transaction = {
        "schema": validator.TRANSACTION_SCHEMA,
        "transaction_id": transaction_id,
        "generated_at": "2026-09-03T11:55:00Z",
        "expires_at": "2026-09-03T13:00:00Z",
        "host": "spot-core",
        "repository_head": "1" * 40,
        "design_review": copy.deepcopy(validator.DESIGN_REVIEW),
        "implementation_review": implementation_review,
        "implementation": [
            {"path": path, "sha256": implementation_sha[path]}
            for path in validator.IMPLEMENTATION_PATHS
        ],
        "operator_authorization": {
            "authorization_id": authorization_id,
            "record_path": f"watch/review/bundles/{authorization_id}.json",
            "record_sha256": "4" * 64,
            "single_use": True,
            "consumed": False,
        },
        "backup": {
            "backup_id": "BACKUP-STORAGE-POST239-K21D-20260903T120000Z",
            "root": "/mnt/collective/backups/spot-core/post239-k21d-storage",
            "binding_id": "BACKUP-BINDING-STORAGE-POST239-K21D-20260903T120000Z",
            "create_before_mutation": True,
            "verified_before_mutation": True,
        },
        "rollback": {
            "document_path": "watch/storage/post239-k21d-scoped-nfs-storage-rollback.md",
            "document_sha256": implementation_sha[
                "watch/storage/post239-k21d-scoped-nfs-storage-rollback.md"
            ],
            "binding_id": "ROLLBACK-BINDING-STORAGE-POST239-K21D-20260903T120000Z",
            "verified": True,
        },
        "mounts": mounts,
        "preserved_objects": copy.deepcopy(list(validator.PRESERVED_OBJECTS)),
        "governance": copy.deepcopy(validator.TRANSACTION_GOVERNANCE),
        "status": validator.TRANSACTION_STATUS,
    }
    authorization = {
        "schema": validator.AUTHORIZATION_SCHEMA,
        "authorization_id": authorization_id,
        "transaction_id": transaction_id,
        "generated_at": "2026-09-03T11:50:00Z",
        "expires_at": "2026-09-03T14:00:00Z",
        "authorized_by": {
            "role": "operator",
            "identity": "offline-test-operator",
            "authority": "single_use_scoped_nfs_storage_only",
        },
        "repository": {
            "host": "spot-core",
            "branch": "main",
            "head": transaction["repository_head"],
            "required_clean_except_runtime_drift": validator.RUNTIME_DRIFT,
        },
        "review": {
            "review_id": implementation_review["review_id"],
            "result_path": implementation_review["result_path"],
            "result_sha256": implementation_review["result_sha256"],
            "verdict": "PASS",
        },
        "scope": copy.deepcopy(validator.AUTHORIZATION_SCOPE),
        "replay_control": {
            "single_use": True,
            "consumed": False,
            "completed": False,
            "rollback_completed": False,
        },
        "governance": copy.deepcopy(validator.AUTHORIZATION_GOVERNANCE),
        "status": validator.AUTHORIZATION_STATUS,
    }
    return transaction, authorization


def test_validator_denials(validator: Any) -> int:
    transaction, authorization = valid_contract(validator)
    validator.validate_transaction(
        transaction,
        Path("/offline/repository"),
        reference_checks=False,
        now=NOW,
    )
    validator.validate_authorization(authorization, transaction, now=NOW)

    cases: list[tuple[str, Any, str]] = []
    changed = copy.deepcopy(transaction)
    changed["governance"]["docker_restart_allowed"] = True
    cases.append(("docker authority", changed, "governance mismatch"))
    changed = copy.deepcopy(transaction)
    changed["governance"]["k21d_installation_allowed"] = True
    cases.append(("K21D installation authority", changed, "governance mismatch"))
    changed = copy.deepcopy(transaction)
    changed["mounts"][0]["source"] = "192.168.50.10:/volume1/docker"
    cases.append(("wrong NFS source", changed, "source mismatch"))
    changed = copy.deepcopy(transaction)
    changed["preserved_objects"] = changed["preserved_objects"][:-1]
    cases.append(("missing preserved record", changed, "preserved object set mismatch"))
    changed = copy.deepcopy(transaction)
    changed["expires_at"] = "2026-09-03T11:59:00Z"
    cases.append(("expired transaction", changed, "expired or not yet valid"))
    changed = copy.deepcopy(transaction)
    changed["implementation_review"]["bundle_path"] = (
        "watch/review/bundles/UNBOUND-IMPLEMENTATION-REVIEW.md"
    )
    cases.append(
        ("unbound implementation review", changed, "bundle path mismatch")
    )

    for _label, payload, fragment in cases:
        expect_validation_denial(
            validator,
            lambda payload=payload: validator.validate_transaction(
                payload,
                Path("/offline/repository"),
                reference_checks=False,
                now=NOW,
            ),
            fragment,
        )

    changed_auth = copy.deepcopy(authorization)
    changed_auth["scope"]["docker_restart_authorized"] = True
    expect_validation_denial(
        validator,
        lambda: validator.validate_authorization(changed_auth, transaction, now=NOW),
        "scope mismatch",
    )
    changed_auth = copy.deepcopy(authorization)
    changed_auth["replay_control"]["consumed"] = True
    expect_validation_denial(
        validator,
        lambda: validator.validate_authorization(changed_auth, transaction, now=NOW),
        "replay state invalid",
    )
    changed_auth = copy.deepcopy(authorization)
    changed_auth["authorization_id"] = (
        "AUTH-STORAGE-POST239-K21D-20260903T120001Z"
    )
    expect_validation_denial(
        validator,
        lambda: validator.validate_authorization(changed_auth, transaction, now=NOW),
        "authorization ID mismatch",
    )

    with tempfile.TemporaryDirectory(prefix="k21d-storage-revocation.") as temporary:
        repository = Path(temporary)
        review_directory = repository / "watch/review/bundles"
        review_directory.mkdir(parents=True)
        revocation = {
            "revoked_authorization_id": authorization["authorization_id"]
        }
        (review_directory / "REVOKE-STORAGE-POST239-K21D-test.json").write_text(
            json.dumps(revocation) + "\n",
            encoding="utf-8",
        )
        expect_validation_denial(
            validator,
            lambda: validator.validate_no_revocation(
                repository,
                transaction["operator_authorization"]["record_path"],
                authorization["authorization_id"],
                transaction["operator_authorization"]["record_sha256"],
            ),
            "authorization revoked",
        )
    return len(cases) + 4


def main() -> int:
    execution = load(EXECUTION_TEST, "k21d_storage_execution_fixture")
    module = execution.load_executor()
    validator = load(VALIDATOR, "k21d_storage_validator_failure_test")
    test_start_failure_rolls_back(execution, module)
    test_replay_collision_denied_before_backup(execution, module)
    test_nfs_collision_fails_closed(execution, module)
    test_changed_unit_is_retained(execution, module)
    validation_denials = test_validator_denials(validator)
    print("[PASS] K21D scoped NFS storage failure test")
    print("execution_failure_cases=4")
    print(f"validation_denial_cases={validation_denials}")
    print("rollback_success_and_incomplete_paths_tested=true")
    print("NFS_overwrite_denied=true")
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
