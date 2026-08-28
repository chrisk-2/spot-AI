#!/usr/bin/env python3
"""Adversarial offline tests for the K21D transaction validator."""

from __future__ import annotations

import copy
import importlib.util
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

BASE = Path(__file__).resolve().parent
VALIDATOR = BASE / "controlled-read-observe-install-transaction-validate.py"


def load_validator() -> Any:
    spec = importlib.util.spec_from_file_location("k21d_validator", VALIDATOR)

    if spec is None or spec.loader is None:
        raise AssertionError("cannot load K21D validator")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def baseline(module: Any) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    files = []

    for source, destination, mode in module.FILE_MAP:
        files.append(
            {
                "source": source,
                "destination": destination,
                "source_sha256": "1" * 64,
                "mode": mode,
                "owner": "root",
                "group": "root",
                "destination_preexisting": False,
                "destination_type_before": "absent",
                "backup_sha256": None,
            }
        )

    return {
        "schema": module.SCHEMA_NAME,
        "transaction_id": "INSTALL-POST239-K21D-SELFTEST0001",
        "generated_at": now.isoformat(),
        "expires_at": (now + timedelta(minutes=30)).isoformat(),
        "host": "spot-core",
        "repository_head": "2" * 40,
        "design_review": {
            "record_path":
                "watch/review/bundles/"
                "POST239-K21D-BLUEPRINT-PASS-20260828T150447Z.json",
            "record_sha256": "3" * 64,
            "verdict": "PASS",
        },
        "operator_authorization": {
            "authorization_id":
                "AUTH-POST239-K21D-INSTALLATION-SELFTEST0001",
            "record_path":
                "watch/review/bundles/"
                "AUTH-POST239-K21D-INSTALLATION-SELFTEST0001.json",
            "record_sha256": "4" * 64,
            "system_path_installation_authorized": True,
            "single_use": True,
            "consumed": False,
        },
        "backup": {
            "manifest_id": "BACKUP-POST239-K21D-SELFTEST0001",
            "manifest_path":
                "/mnt/collective/backups/spot-core/post239-k21d/"
                "BACKUP-POST239-K21D-SELFTEST0001.json",
            "manifest_sha256": "5" * 64,
            "binding_id":
                "BACKUP-BINDING-POST239-K21D-SELFTEST0001",
            "verified": True,
        },
        "rollback": {
            "document_path":
                "watch/observe/"
                "controlled-read-observe-install-rollback.md",
            "document_sha256": "6" * 64,
            "binding_id":
                "ROLLBACK-BINDING-POST239-K21D-SELFTEST0001",
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
        "status": module.STATUS,
    }


def rejected(
    module: Any,
    value: dict[str, Any],
    label: str,
    mutate: Callable[[dict[str, Any]], None],
) -> None:
    candidate = copy.deepcopy(value)
    mutate(candidate)

    try:
        module.validate_transaction(
            candidate,
            BASE.parent.parent,
            verify_references=False,
        )
    except module.TransactionError:
        print(f"[PASS] rejected: {label}")
        return

    raise AssertionError(f"unsafe transaction accepted: {label}")


def main() -> int:
    module = load_validator()
    value = baseline(module)

    module.validate_transaction(
        value,
        BASE.parent.parent,
        verify_references=False,
    )
    print("[PASS] valid offline K21D transaction accepted")

    cases = [
        (
            "unexpected field",
            lambda item: item.update({"unexpected": True}),
        ),
        (
            "wrong host",
            lambda item: item.update({"host": "spot-worker-05"}),
        ),
        (
            "expired transaction",
            lambda item: item.update(
                {"expires_at": item["generated_at"]}
            ),
        ),
        (
            "review not PASS",
            lambda item: item["design_review"].update({"verdict": "NO"}),
        ),
        (
            "installation authorization false",
            lambda item: item["operator_authorization"].update(
                {"system_path_installation_authorized": False}
            ),
        ),
        (
            "authorization not single-use",
            lambda item: item["operator_authorization"].update(
                {"single_use": False}
            ),
        ),
        (
            "authorization consumed",
            lambda item: item["operator_authorization"].update(
                {"consumed": True}
            ),
        ),
        (
            "backup not verified",
            lambda item: item["backup"].update({"verified": False}),
        ),
        (
            "backup path escape",
            lambda item: item["backup"].update(
                {"manifest_path": "/tmp/backup.json"}
            ),
        ),
        (
            "rollback not verified",
            lambda item: item["rollback"].update({"verified": False}),
        ),
        (
            "file omitted",
            lambda item: item["files"].pop(),
        ),
        (
            "source substituted",
            lambda item: item["files"][0].update(
                {"source": "watch/observe/other.py"}
            ),
        ),
        (
            "destination substituted",
            lambda item: item["files"][0].update(
                {"destination": "/tmp/observer.py"}
            ),
        ),
        (
            "mode expanded",
            lambda item: item["files"][0].update({"mode": "0777"}),
        ),
        (
            "unconditional daemon-reload",
            lambda item: item["planned_service_state"].update(
                {"unconditional_daemon_reload": True}
            ),
        ),
        (
            "service start planned",
            lambda item: item["planned_service_state"].update(
                {"service_start_planned": True}
            ),
        ),
        (
            "service enablement planned",
            lambda item: item["planned_service_state"].update(
                {"service_enablement_planned": True}
            ),
        ),
        (
            "timer installation planned",
            lambda item: item["planned_service_state"].update(
                {"timer_installation_planned": True}
            ),
        ),
        (
            "request dispatch planned",
            lambda item: item["planned_service_state"].update(
                {"request_dispatch_planned": True}
            ),
        ),
        (
            "production observation planned",
            lambda item: item["planned_service_state"].update(
                {"production_observation_planned": True}
            ),
        ),
        (
            "worker self-apply",
            lambda item: item["governance"].update(
                {"worker_self_apply_allowed": True}
            ),
        ),
        (
            "activation authority expanded",
            lambda item: item["governance"].update(
                {"activation_authorized": True}
            ),
        ),
        (
            "execution authority expanded",
            lambda item: item["governance"].update(
                {"execution_allowed": True}
            ),
        ),
        (
            "mutation authority expanded",
            lambda item: item["governance"].update(
                {"mutation_authority": True}
            ),
        ),
    ]

    for label, mutate in cases:
        rejected(module, value, label, mutate)

    print("positive_tests=1")
    print(f"negative_tests={len(cases)}")
    print("installation_manifest_created=false")
    print("backup_created=false")
    print("installation_performed=false")
    print("daemon_reload_performed=false")
    print("execution_allowed=false")
    print("mutation_authority=false")
    print("RESULT: POST-2.39 K21D FAILURE TEST PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
