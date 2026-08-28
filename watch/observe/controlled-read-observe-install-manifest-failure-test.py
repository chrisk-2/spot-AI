#!/usr/bin/env python3
"""Adversarial tests for the K21C installation-manifest validator."""

from __future__ import annotations

import copy
import hashlib
import importlib.util
import sys
from pathlib import Path
from typing import Any, Callable

BASE = Path(__file__).resolve().parent
REPOSITORY = BASE.parent.parent
VALIDATOR = BASE / "controlled-read-observe-install-manifest-validate.py"


def load_validator() -> Any:
    spec = importlib.util.spec_from_file_location(
        "k21c_install_manifest_validator",
        VALIDATOR,
    )

    if spec is None or spec.loader is None:
        raise AssertionError("cannot load manifest validator")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def valid_manifest(module: Any) -> dict[str, Any]:
    files = []

    for source, (destination, mode) in module.FILE_MAP.items():
        files.append(
            {
                "source": source,
                "destination": destination,
                "sha256": sha256_file(REPOSITORY / source),
                "mode": mode,
                "owner": "root",
                "group": "root",
                "destination_preexisting": False,
            }
        )

    rollback = (
        REPOSITORY /
        "watch/observe/"
        "controlled-read-observe-install-rollback.md"
    )

    return {
        "schema": module.SCHEMA,
        "manifest_id": "INSTALL-POST239-K21C-SELFTEST0001",
        "generated_at": "2026-08-26T15:00:00Z",
        "host": "spot-core",
        "repository_head": "1" * 40,
        "authorization": {
            "authorization_id":
                "AUTH-POST239-K21C-INSTALLATION-SELFTEST0001",
            "record_path":
                "watch/review/bundles/"
                "AUTH-POST239-K21C-INSTALLATION-SELFTEST0001.json",
            "record_sha256": "2" * 64,
            "system_path_installation_authorized": False,
        },
        "review": {
            "review_pass_path":
                "watch/review/bundles/"
                "POST239-K21C-INSTALLATION-PASS-SELFTEST0001.json",
            "review_pass_sha256": "3" * 64,
            "verdict": "PASS",
        },
        "backup": {
            "backup_manifest_id": "BACKUP-MANIFEST-SELFTEST0001",
            "backup_manifest_path":
                "/mnt/collective/backups/spot-core/post239-k21c/"
                "BACKUP-POST239-K21C-SELFTEST0001.json",
            "backup_manifest_sha256": "4" * 64,
            "backup_verified": True,
            "backup_binding_id": "BACKUP-BINDING-SELFTEST0001",
            "backup_binding_verified": True,
        },
        "rollback": {
            "rollback_document":
                "watch/observe/"
                "controlled-read-observe-install-rollback.md",
            "rollback_document_sha256": sha256_file(rollback),
            "rollback_defined": True,
            "rollback_binding_id": "ROLLBACK-BINDING-SELFTEST0001",
            "rollback_binding_verified": True,
        },
        "files": files,
        "runtime": {
            "request_file":
                "/var/lib/spot/controlled-read-observe/request.json",
            "request_file_mode": "0600",
            "evidence_directory":
                "/var/lib/spot/controlled-read-observe/evidence",
            "evidence_directory_mode": "0700",
            "runtime_owner": "root",
        },
        "planned_service_state": {
            "daemon_reload_planned": False,
            "service_activation_planned": False,
            "timer_installation_planned": False,
            "observer_enabled": False,
            "observer_scheduled": False,
        },
        "governance": {
            "spot_core_sole_authority": True,
            "worker_self_apply_allowed": False,
            "activation_authorized": False,
            "scheduling_authorized": False,
            "production_observation_authorized": False,
            "live_executor_enabled": False,
            "execution_allowed": False,
            "mutation_authority": False,
        },
        "status": module.STATUS,
    }


def rejected(
    module: Any,
    baseline: dict[str, Any],
    label: str,
    mutate: Callable[[dict[str, Any]], None],
) -> None:
    candidate = copy.deepcopy(baseline)
    mutate(candidate)

    try:
        module.validate_manifest(
            candidate,
            REPOSITORY,
            verify_references=False,
        )
    except module.ManifestError:
        print(f"[PASS] rejected: {label}")
        return

    raise AssertionError(f"unsafe manifest accepted: {label}")


def main() -> int:
    module = load_validator()
    baseline = valid_manifest(module)

    module.validate_manifest(
        baseline,
        REPOSITORY,
        verify_references=False,
    )
    print("[PASS] complete valid offline manifest accepted")

    cases: list[
        tuple[str, Callable[[dict[str, Any]], None]]
    ] = [
        (
            "unexpected top-level field",
            lambda value: value.update({"unexpected": True}),
        ),
        (
            "invalid timestamp",
            lambda value: value.update({"generated_at": "not-a-time"}),
        ),
        (
            "wrong host",
            lambda value: value.update({"host": "spot-worker-05"}),
        ),
        (
            "system-path authorization expansion",
            lambda value: value["authorization"].update(
                {"system_path_installation_authorized": True}
            ),
        ),
        (
            "authorization path escape",
            lambda value: value["authorization"].update(
                {"record_path": "../authorization.json"}
            ),
        ),
        (
            "review verdict not PASS",
            lambda value: value["review"].update({"verdict": "NO"}),
        ),
        (
            "backup not verified",
            lambda value: value["backup"].update(
                {"backup_verified": False}
            ),
        ),
        (
            "backup binding not verified",
            lambda value: value["backup"].update(
                {"backup_binding_verified": False}
            ),
        ),
        (
            "backup path outside fixed root",
            lambda value: value["backup"].update(
                {"backup_manifest_path": "/tmp/backup.json"}
            ),
        ),
        (
            "rollback not defined",
            lambda value: value["rollback"].update(
                {"rollback_defined": False}
            ),
        ),
        (
            "rollback binding not verified",
            lambda value: value["rollback"].update(
                {"rollback_binding_verified": False}
            ),
        ),
        (
            "file omitted",
            lambda value: value["files"].pop(),
        ),
        (
            "destination substitution",
            lambda value: value["files"][0].update(
                {"destination": "/tmp/controlled-read-observe.py"}
            ),
        ),
        (
            "source hash mismatch",
            lambda value: value["files"][0].update(
                {"sha256": "f" * 64}
            ),
        ),
        (
            "source mode expansion",
            lambda value: value["files"][0].update({"mode": "0777"}),
        ),
        (
            "daemon-reload planned",
            lambda value: value["planned_service_state"].update(
                {"daemon_reload_planned": True}
            ),
        ),
        (
            "service activation planned",
            lambda value: value["planned_service_state"].update(
                {"service_activation_planned": True}
            ),
        ),
        (
            "timer installation planned",
            lambda value: value["planned_service_state"].update(
                {"timer_installation_planned": True}
            ),
        ),
        (
            "observer enabled",
            lambda value: value["planned_service_state"].update(
                {"observer_enabled": True}
            ),
        ),
        (
            "observer scheduled",
            lambda value: value["planned_service_state"].update(
                {"observer_scheduled": True}
            ),
        ),
        (
            "worker self-apply enabled",
            lambda value: value["governance"].update(
                {"worker_self_apply_allowed": True}
            ),
        ),
        (
            "activation authority expanded",
            lambda value: value["governance"].update(
                {"activation_authorized": True}
            ),
        ),
        (
            "production observation authority expanded",
            lambda value: value["governance"].update(
                {"production_observation_authorized": True}
            ),
        ),
        (
            "execution authority expanded",
            lambda value: value["governance"].update(
                {"execution_allowed": True}
            ),
        ),
        (
            "mutation authority expanded",
            lambda value: value["governance"].update(
                {"mutation_authority": True}
            ),
        ),
    ]

    for label, mutate in cases:
        rejected(module, baseline, label, mutate)

    try:
        module.validate_manifest(
            baseline,
            REPOSITORY,
            verify_references=True,
        )
    except module.ManifestError as exc:
        if "missing" not in str(exc):
            raise
        print("[PASS] missing correlated artifacts fail closed")
    else:
        raise AssertionError(
            "uncreated correlated artifacts unexpectedly validated"
        )

    print(f"positive_tests=1")
    print(f"negative_tests={len(cases) + 1}")
    print("installation_manifest_created=false")
    print("backup_artifact_created=false")
    print("installation_performed=false")
    print("activation_authorized=false")
    print("observer_installed=false")
    print("observer_enabled=false")
    print("observer_scheduled=false")
    print("production_observation_performed=false")
    print("execution_allowed=false")
    print("mutation_authority=false")
    print("RESULT: POST-2.39 K21C MANIFEST FAILURE TEST PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
