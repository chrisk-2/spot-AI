#!/usr/bin/env python3
"""Offline validation of the K21C installation contract."""

from __future__ import annotations

import configparser
import json
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent
UNIT = BASE / "controlled-read-observe.service"
RUNNER = BASE / "controlled-read-observe.py"
VALIDATION_MODULE = BASE / "controlled_read_observe_validation_v1.py"
REQUEST_VALIDATOR = BASE / "controlled-read-observe-request-validate.py"
EVIDENCE_VALIDATOR = BASE / "controlled-read-observe-evidence-validate.py"
ALLOWLIST = BASE / "controlled-read-observe-allowlist-v1.json"
REQUEST_SCHEMA = BASE / "controlled-read-observe-request-schema-v1.json"
EVIDENCE_SCHEMA = BASE / "controlled-read-observe-evidence-schema-v1.json"
BLUEPRINT = BASE / "POST239-K21C-INSTALLATION-ACTIVATION-BLUEPRINT.md"
ROLLBACK = BASE / "controlled-read-observe-install-rollback.md"
MANIFEST_SCHEMA = (
    BASE / "controlled-read-observe-install-manifest-schema-v1.json"
)
MANIFEST_VALIDATOR = (
    BASE / "controlled-read-observe-install-manifest-validate.py"
)
MANIFEST_FAILURE_TEST = (
    BASE / "controlled-read-observe-install-manifest-failure-test.py"
)

EXPECTED_EXEC = (
    "ExecStart=/usr/bin/python3 "
    "/usr/local/lib/spot/observe/controlled-read-observe.py "
    "--request /var/lib/spot/controlled-read-observe/request.json "
    "--evidence-dir /var/lib/spot/controlled-read-observe/evidence"
)

REQUIRED_UNIT_LINES = {
    "Type=oneshot",
    "User=root",
    "Group=root",
    "NoNewPrivileges=true",
    "PrivateTmp=true",
    "PrivateDevices=true",
    "PrivateNetwork=true",
    "ProtectSystem=strict",
    "ProtectHome=true",
    "ProtectKernelTunables=true",
    "ProtectKernelModules=true",
    "ProtectKernelLogs=true",
    "ProtectControlGroups=true",
    "ProtectClock=true",
    "ProtectHostname=true",
    "ProtectProc=invisible",
    "ProcSubset=pid",
    "RestrictSUIDSGID=true",
    "LockPersonality=true",
    "MemoryDenyWriteExecute=true",
    "RestrictRealtime=true",
    "RestrictNamespaces=true",
    "RemoveIPC=true",
    "CapabilityBoundingSet=",
    "AmbientCapabilities=",
    "RestrictAddressFamilies=AF_UNIX",
    "SystemCallArchitectures=native",
    "UMask=0077",
    "ReadOnlyPaths=/etc/spot/observe",
    "ReadOnlyPaths=/var/lib/spot/controlled-read-observe/request.json",
    "ReadWritePaths=/var/lib/spot/controlled-read-observe/evidence",
}

FORBIDDEN_UNIT_TOKENS = (
    "[Install]",
    "WantedBy=",
    "RequiredBy=",
    "Alias=",
    "Also=",
    "Restart=",
    "ExecStartPre=",
    "ExecStartPost=",
    "ExecReload=",
    "ExecStop=",
    "ExecStopPost=",
    "--offline-validation-fixture",
    "systemctl",
    "journalctl",
    ".timer",
)

FORBIDDEN_RUNNER_TOKENS = (
    "subprocess",
    "os.system",
    "shell=True",
    "systemctl",
    "journalctl",
    "urllib",
    "requests",
    "paramiko",
    "ssh ",
)

EXPECTED_INSTALL_TARGETS = {
    "controlled-read-observe.py":
        "/usr/local/lib/spot/observe/controlled-read-observe.py",
    "controlled_read_observe_validation_v1.py":
        "/usr/local/lib/spot/observe/"
        "controlled_read_observe_validation_v1.py",
    "controlled-read-observe-request-validate.py":
        "/usr/local/lib/spot/observe/"
        "controlled-read-observe-request-validate.py",
    "controlled-read-observe-evidence-validate.py":
        "/usr/local/lib/spot/observe/"
        "controlled-read-observe-evidence-validate.py",
    "controlled-read-observe-allowlist-v1.json":
        "/etc/spot/observe/"
        "controlled-read-observe-allowlist-v1.json",
    "controlled-read-observe-request-schema-v1.json":
        "/etc/spot/observe/"
        "controlled-read-observe-request-schema-v1.json",
    "controlled-read-observe-evidence-schema-v1.json":
        "/etc/spot/observe/"
        "controlled-read-observe-evidence-schema-v1.json",
    "controlled-read-observe.service":
        "/etc/systemd/system/spot-controlled-read-observe.service",
}


def fail(message: str) -> None:
    raise AssertionError(message)


def load_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"cannot load JSON {path.name}: {exc}")

    if not isinstance(value, dict):
        fail(f"JSON top level must be an object: {path.name}")

    return value


def validate_required_sources() -> None:
    paths = (
        UNIT,
        RUNNER,
        VALIDATION_MODULE,
        REQUEST_VALIDATOR,
        EVIDENCE_VALIDATOR,
        ALLOWLIST,
        REQUEST_SCHEMA,
        EVIDENCE_SCHEMA,
        BLUEPRINT,
        ROLLBACK,
        MANIFEST_SCHEMA,
        MANIFEST_VALIDATOR,
        MANIFEST_FAILURE_TEST,
    )

    for path in paths:
        if not path.is_file() or path.stat().st_size == 0:
            fail(f"required source missing or empty: {path}")

    print("[PASS] required installation sources present")


def validate_unit() -> None:
    text = UNIT.read_text(encoding="utf-8")

    for token in FORBIDDEN_UNIT_TOKENS:
        if token in text:
            fail(f"forbidden unit surface present: {token}")

    lines = {
        line.strip()
        for line in text.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    }

    missing = sorted(REQUIRED_UNIT_LINES - lines)
    if missing:
        fail(f"required unit controls missing: {missing}")

    if text.count(EXPECTED_EXEC) != 1:
        fail("unit must contain exactly one fixed ExecStart")

    parser = configparser.ConfigParser(
        interpolation=None,
        strict=False,
    )
    parser.optionxform = str
    parser.read_string(text)

    if set(parser.sections()) != {"Unit", "Service"}:
        fail(f"unexpected unit sections: {sorted(parser.sections())}")

    if parser["Service"].get("Type") != "oneshot":
        fail("service must use Type=oneshot")

    if parser["Service"].get("PrivateNetwork") != "true":
        fail("service must use PrivateNetwork=true")

    print("[PASS] unit is fixed-path, hardened, and non-enableable")


def validate_runner() -> None:
    text = RUNNER.read_text(encoding="utf-8")

    for token in FORBIDDEN_RUNNER_TOKENS:
        if token in text:
            fail(f"forbidden runner surface present: {token}")

    required = (
        'parser.add_argument("--request", required=True, type=Path)',
        'parser.add_argument("--evidence-dir", type=Path)',
        '"policy_decision": "denied_fail_closed"',
        "os.O_WRONLY | os.O_CREAT | os.O_EXCL",
        "observation identity collision with different evidence",
    )

    for token in required:
        if token not in text:
            fail(f"required runner control absent: {token}")

    if text.count("--offline-validation-fixture") != 1:
        fail("offline fixture interface count is unexpected")

    print("[PASS] runner remains dormant and replay-safe")


def validate_allowlist() -> None:
    allowlist = load_json(ALLOWLIST)

    expected_false = (
        "activation_authorized",
        "observer_installed",
        "observer_enabled",
        "observer_scheduled",
    )

    if allowlist.get("status") != "inactive":
        fail("allowlist status must remain inactive")

    if allowlist.get("implementation_present") is not True:
        fail("implementation_present must be true")

    for field in expected_false:
        if allowlist.get(field) is not False:
            fail(f"inactive-state field must remain false: {field}")

    governance = allowlist.get("governance")
    if not isinstance(governance, dict):
        fail("governance object missing")

    for field in (
        "execution_allowed",
        "live_executor_enabled",
        "mutation_authority",
        "network_mutation_allowed",
        "remediation_allowed",
        "remote_execution_allowed",
        "service_action_allowed",
    ):
        if governance.get(field) is not False:
            fail(f"governance field must remain false: {field}")

    print("[PASS] allowlist remains inactive and non-authoritative")


def validate_schemas() -> None:
    request_schema = load_json(REQUEST_SCHEMA)
    evidence_schema = load_json(EVIDENCE_SCHEMA)
    install_schema = load_json(MANIFEST_SCHEMA)

    if request_schema.get("additionalProperties") is not False:
        fail("request schema must reject additional properties")

    if evidence_schema.get("additionalProperties") is not False:
        fail("evidence schema must reject additional properties")

    request_properties = request_schema.get("properties", {})
    evidence_properties = evidence_schema.get("properties", {})

    for field in (
        "execution_allowed",
        "mutation_authority",
        "live_executor_enabled",
    ):
        if request_properties.get(field, {}).get("const") is not False:
            fail(f"request schema authority field not locked: {field}")

        if evidence_properties.get(field, {}).get("const") is not False:
            fail(f"evidence schema authority field not locked: {field}")

    for field in (
        "remediation_performed",
        "service_action_performed",
        "network_stack_mutation",
    ):
        if evidence_properties.get(field, {}).get("const") is not False:
            fail(f"evidence mutation field not locked: {field}")

    if install_schema.get("additionalProperties") is not False:
        fail("installation manifest schema must reject additional properties")

    install_required = install_schema.get("required")
    if not isinstance(install_required, list):
        fail("installation manifest required-field list missing")

    if len(install_required) != 14:
        fail("installation manifest must require fourteen top-level fields")

    install_properties = install_schema.get("properties", {})

    if (
        install_properties.get("files", {}).get("minItems") != 8
        or install_properties.get("files", {}).get("maxItems") != 8
    ):
        fail("installation manifest must require exactly eight files")

    install_authorization = (
        install_properties.get("authorization", {}).get("properties", {})
    )

    if (
        install_authorization
        .get("system_path_installation_authorized", {})
        .get("const")
        is not False
    ):
        fail("system-path installation authority must remain false")

    planned_service_state = (
        install_properties
        .get("planned_service_state", {})
        .get("properties", {})
    )

    if (
        planned_service_state
        .get("daemon_reload_planned", {})
        .get("const")
        is not False
    ):
        fail("daemon-reload planning must remain false")

    install_governance = (
        install_properties.get("governance", {}).get("properties", {})
    )

    for field in (
        "activation_authorized",
        "scheduling_authorized",
        "production_observation_authorized",
        "live_executor_enabled",
        "execution_allowed",
        "mutation_authority",
    ):
        if install_governance.get(field, {}).get("const") is not False:
            fail(f"installation governance field not locked: {field}")

    print("[PASS] request, evidence, and install schemas fail closed")


def validate_blueprint() -> None:
    text = BLUEPRINT.read_text(encoding="utf-8")

    required = (
        "DESIGN AND REVIEW ONLY",
        "Installation does not imply activation.",
        "timer unit absent",
        "installation authorized: false",
        "observer installed: false",
        "observer enabled: false",
        "observer scheduled: false",
        "activation authorized: false",
        "production observation authorized: false",
        "execution allowed: false",
        "mutation authority: false",
    )

    for token in required:
        if token not in text:
            fail(f"blueprint control absent: {token}")

    for source, destination in EXPECTED_INSTALL_TARGETS.items():
        if source not in text:
            fail(f"blueprint source identity absent: {source}")

        if destination not in text:
            fail(f"blueprint destination absent: {destination}")

    print("[PASS] blueprint fixes the complete installation boundary")


def validate_installation_toolchain() -> None:
    rollback = ROLLBACK.read_text(encoding="utf-8")

    for token in (
        "ROLLBACK DESIGN ONLY",
        "No verified backup and binding means no installation.",
        "rollback execution authorized: false",
        "production observation authorized: false",
        "execution allowed: false",
        "mutation authority: false",
    ):
        if token not in rollback:
            fail(f"rollback control absent: {token}")

    validator_source = MANIFEST_VALIDATOR.read_text(encoding="utf-8")
    failure_source = MANIFEST_FAILURE_TEST.read_text(encoding="utf-8")

    for token in (
        "system-path installation authority expanded",
        "daemon-reload planning authority expanded",
        "manifest must contain exactly eight files",
        "source hash mismatch",
        "unsafe governance state",
        "AUTH_PATH_PATTERN.fullmatch",
        "REVIEW_PATH_PATTERN.fullmatch",
        "BACKUP_PATH_PATTERN.fullmatch",
    ):
        if token not in validator_source:
            fail(f"manifest validator control absent: {token}")

    for token in (
        "complete valid offline manifest accepted",
        "system-path authorization expansion",
        "daemon-reload planned",
        "backup not verified",
        "timer installation planned",
        "production observation authority expanded",
        "mutation authority expanded",
        "missing correlated artifacts fail closed",
    ):
        if token not in failure_source:
            fail(f"manifest failure test absent: {token}")

    print("[PASS] rollback and manifest validation toolchain complete")


def main() -> int:
    validate_required_sources()
    validate_unit()
    validate_runner()
    validate_allowlist()
    validate_schemas()
    validate_blueprint()
    validate_installation_toolchain()

    print("pass=7 fail=0")
    print("installation_artifacts_valid=true")
    print("system_path_installation_authorized=false")
    print("installation_performed=false")
    print("daemon_reload_performed=false")
    print("activation_authorized=false")
    print("observer_installed=false")
    print("observer_enabled=false")
    print("observer_scheduled=false")
    print("production_observation_performed=false")
    print("execution_allowed=false")
    print("mutation_authority=false")
    print("RESULT: POST-2.39 K21C INSTALL CONTRACT VALIDATION PASS")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        print("RESULT: POST-2.39 K21C INSTALL CONTRACT VALIDATION FAIL")
        raise SystemExit(1)
