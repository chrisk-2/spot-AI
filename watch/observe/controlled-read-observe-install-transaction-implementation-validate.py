#!/usr/bin/env python3
"""Offline validation of the complete dormant K21D toolchain."""

from pathlib import Path
import subprocess
import sys

BASE = Path(__file__).resolve().parent

FILES = (
    BASE / "controlled-read-observe-install-transaction-schema-v1.json",
    BASE / "controlled-read-observe-install-transaction-validate.py",
    BASE / "controlled-read-observe-install-transaction-failure-test.py",
    BASE / "controlled-read-observe-install-transaction.py",
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> int:
    for path in FILES:
        require(path.is_file() and path.stat().st_size > 0, f"missing {path}")

    installer = FILES[-1]
    source = installer.read_text(encoding="utf-8")

    for token in (
        "cannot install files",
        "--offline-self-test",
        "--execute",
        "installation execution is not implemented or authorized",
        "installation_performed=false",
        "execution_allowed=false",
        "mutation_authority=false",
    ):
        require(token in source, f"dormant control absent: {token}")

    allowed = subprocess.run(
        [sys.executable, str(installer), "--offline-self-test"],
        capture_output=True,
        text=True,
        check=False,
    )
    require(allowed.returncode == 0, "offline self-test failed")
    require("[PASS] K21D installer is dormant" in allowed.stdout, "bad PASS")

    denied = subprocess.run(
        [sys.executable, str(installer), "--execute"],
        capture_output=True,
        text=True,
        check=False,
    )
    require(denied.returncode == 2, "execute request did not fail closed")
    require("[DENY]" in denied.stderr, "execute denial absent")

    default = subprocess.run(
        [sys.executable, str(installer)],
        capture_output=True,
        text=True,
        check=False,
    )
    require(default.returncode == 2, "default invocation did not fail closed")

    print("[PASS] complete K21D dormant toolchain")
    print("pass=4 fail=0")
    print("system_path_installation_authorized=false")
    print("backup_created=false")
    print("installation_manifest_created=false")
    print("authorization_consumed=false")
    print("installation_performed=false")
    print("daemon_reload_performed=false")
    print("activation_authorized=false")
    print("execution_allowed=false")
    print("mutation_authority=false")
    print("RESULT: POST-2.39 K21D IMPLEMENTATION VALIDATION PASS")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        raise SystemExit(1)
