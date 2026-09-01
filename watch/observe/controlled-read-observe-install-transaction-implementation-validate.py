#!/usr/bin/env python3
"""Offline integration validation for the reviewed K21D live executor candidate.

This validator never invokes the executor's live ``--execute`` path. It checks
the hash-pinned repository candidate, runs its static self-test, and runs the
disposable execution and transaction-contract regression suites.
"""

from __future__ import annotations

import ast
import hashlib
import os
from pathlib import Path
import subprocess
import sys
from typing import Any


SCRIPT = Path(__file__).resolve()
REPOSITORY = SCRIPT.parents[2]
OBSERVE = REPOSITORY / "watch" / "observe"

INSTALLER = OBSERVE / "controlled-read-observe-install-transaction.py"
EXECUTION_TEST = (
    OBSERVE / "controlled-read-observe-install-transaction-execution-test.py"
)
TRANSACTION_VALIDATOR = (
    OBSERVE / "controlled-read-observe-install-transaction-validate.py"
)
FAILURE_TEST = (
    OBSERVE / "controlled-read-observe-install-transaction-failure-test.py"
)

INSTALLER_SHA256 = (
    "2b30248eb2d5fb4583c0b96003616e204978144f8c2651efc4e6a1804927e325"
)
EXECUTION_TEST_SHA256 = (
    "6810b844fd3ebcbda8290e0cf0a224169ed479cd7577080f49cc25158336b330"
)

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

LIVE_PATHS = tuple(Path(entry[1]) for entry in FILE_MAP)


class ValidationError(RuntimeError):
    """Fail-closed validation error."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def assignment(tree: ast.Module, name: str) -> Any:
    for node in tree.body:
        if isinstance(node, ast.Assign):
            if any(
                isinstance(target, ast.Name) and target.id == name
                for target in node.targets
            ):
                return ast.literal_eval(node.value)
        if (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.target.id == name
        ):
            return ast.literal_eval(node.value)
    raise ValidationError(f"{name} assignment absent")


def normalize_mapping(value: Any, label: str) -> list[tuple[str, str, str]]:
    require(isinstance(value, (list, tuple)), f"{label} must be ordered")
    normalized: list[tuple[str, str, str]] = []
    for entry in value:
        require(
            isinstance(entry, (list, tuple)) and len(entry) == 3,
            f"{label} entry malformed",
        )
        source, destination, mode = entry
        require(
            all(isinstance(item, str) for item in entry),
            f"{label} entry must contain strings",
        )
        normalized.append((source, destination, mode))
    return normalized


def assert_no_live_paths() -> None:
    for path in LIVE_PATHS:
        require(
            not path.exists() and not path.is_symlink(),
            f"live path unexpectedly present: {path}",
        )


def run(command: list[str], label: str, timeout: int = 300) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    result = subprocess.run(
        command,
        cwd=REPOSITORY,
        env=environment,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )
    require(result.returncode == 0, f"{label} failed:\n{result.stdout}{result.stderr}")
    return result


def repository_status() -> str:
    result = run(
        ["git", "status", "--porcelain=v1", "-uall"],
        "repository status",
        timeout=30,
    )
    return result.stdout


def validate_static_contract() -> None:
    required_files = (
        INSTALLER,
        EXECUTION_TEST,
        TRANSACTION_VALIDATOR,
        FAILURE_TEST,
    )
    for path in required_files:
        require(path.is_file(), f"required file absent: {path}")
        require(not path.is_symlink(), f"required file is symlink: {path}")

    require(digest(INSTALLER) == INSTALLER_SHA256, "live executor digest mismatch")
    require(
        digest(EXECUTION_TEST) == EXECUTION_TEST_SHA256,
        "execution-test digest mismatch",
    )

    installer_source = INSTALLER.read_text(encoding="utf-8")
    validator_source = TRANSACTION_VALIDATOR.read_text(encoding="utf-8")
    installer_tree = ast.parse(installer_source, filename=str(INSTALLER))
    validator_tree = ast.parse(validator_source, filename=str(TRANSACTION_VALIDATOR))

    installer_map = normalize_mapping(
        assignment(installer_tree, "FILE_MAP"),
        "executor FILE_MAP",
    )
    validator_map = normalize_mapping(
        assignment(validator_tree, "FILE_MAP"),
        "transaction-validator FILE_MAP",
    )
    require(installer_map == FILE_MAP, "executor mapping differs from K21C/K21D")
    require(validator_map == FILE_MAP, "validator mapping differs from K21C/K21D")

    constants = {
        node.value
        for node in ast.walk(installer_tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }
    require("--offline-self-test" in constants, "offline self-test option absent")
    require("--execute" in constants, "live execute option absent")

    for stale in (
        "This artifact cannot install files",
        "installation execution is not implemented or authorized",
        "K21D installer is dormant",
    ):
        require(stale not in installer_source, f"stale dormant control present: {stale}")

    imported_roots: set[str] = set()
    for node in ast.walk(installer_tree):
        if isinstance(node, ast.Import):
            imported_roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_roots.add(node.module.split(".")[0])
    require(
        imported_roots.isdisjoint({"requests", "httpx", "urllib"}),
        "network client imported by executor",
    )

    for node in ast.walk(installer_tree):
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Name):
            require(node.func.id not in {"eval", "exec"}, "dynamic execution API present")
        if isinstance(node.func, ast.Attribute):
            require(
                not (
                    isinstance(node.func.value, ast.Name)
                    and node.func.value.id == "os"
                    and node.func.attr in {"system", "popen"}
                ),
                "shell execution API present",
            )
        for keyword in node.keywords:
            if keyword.arg == "shell":
                require(
                    not (
                        isinstance(keyword.value, ast.Constant)
                        and keyword.value.value is True
                    ),
                    "shell=True present",
                )


def main() -> int:
    try:
        assert_no_live_paths()
        status_before = repository_status()

        validate_static_contract()
        print("[PASS] hash-pinned live executor and exact mapping")

        self_test = run(
            [sys.executable, str(INSTALLER), "--offline-self-test"],
            "executor static self-test",
        )
        require(
            "[PASS] K21D live executor static self-test" in self_test.stdout,
            "unexpected executor self-test result",
        )
        print("[PASS] live executor static self-test")

        execution = run(
            [sys.executable, str(EXECUTION_TEST)],
            "disposable execution tests",
            timeout=600,
        )
        require(
            "RESULT: POST-2.39 K21D LIVE EXECUTOR OFFLINE TEST PASS"
            in execution.stdout,
            "execution-test PASS marker absent",
        )
        print("[PASS] disposable execution and rollback tests")

        contract = run(
            [sys.executable, str(FAILURE_TEST)],
            "transaction-contract regression",
            timeout=600,
        )
        require(
            "RESULT: POST-2.39 K21D FAILURE TEST PASS" in contract.stdout,
            "transaction-contract PASS marker absent",
        )
        print("[PASS] transaction-contract regression")

        assert_no_live_paths()
        require(repository_status() == status_before, "repository changed during validation")
        print("[PASS] live paths absent and repository unchanged")

    except (OSError, SyntaxError, ValueError, ValidationError, subprocess.TimeoutExpired) as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        print("installation_performed=false", file=sys.stderr)
        print("daemon_reload_performed=false", file=sys.stderr)
        print("activation_authorized=false", file=sys.stderr)
        print("execution_allowed=false", file=sys.stderr)
        print("mutation_authority=false", file=sys.stderr)
        return 1

    print("pass=5 fail=0")
    print("system_path_installation_authorized=false")
    print("backup_created=false")
    print("installation_manifest_created=false")
    print("authorization_consumed=false")
    print("installation_performed=false")
    print("daemon_reload_performed=false")
    print("activation_authorized=false")
    print("scheduling_authorized=false")
    print("production_observation_authorized=false")
    print("execution_allowed=false")
    print("mutation_authority=false")
    print("RESULT: POST-2.39 K21D LIVE IMPLEMENTATION VALIDATION PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
