#!/usr/bin/env python3
"""Fail-closed validation helpers for the inactive controlled observation lane."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from jsonschema import Draft202012Validator, FormatChecker


BASE = Path(__file__).resolve().parent
ALLOWLIST_PATH = BASE / "controlled-read-observe-allowlist-v1.json"
REQUEST_SCHEMA_PATH = BASE / "controlled-read-observe-request-schema-v1.json"
EVIDENCE_SCHEMA_PATH = BASE / "controlled-read-observe-evidence-schema-v1.json"

CLASS_OPERATIONS = {
    "systemd": {
        "systemd_show",
        "systemd_status",
        "systemd_is_active",
        "systemd_is_enabled",
        "systemd_list_units",
        "systemd_list_unit_files",
    },
    "journal": {"journal_read"},
    "socket": {"socket_listening_read"},
    "http": {"http_get"},
    "filesystem": {
        "filesystem_metadata_read",
        "filesystem_bounded_content_read",
    },
    "git": {
        "git_status",
        "git_diff",
        "git_log",
        "git_show",
        "git_rev_parse",
        "git_branch_current",
    },
}

SYSTEMD_GLOBAL_OPERATIONS = {
    "systemd_list_units",
    "systemd_list_unit_files",
}

FALSE_LOCKS = (
    "execution_allowed",
    "mutation_authority",
    "live_executor_enabled",
)

EVIDENCE_FALSE_LOCKS = FALSE_LOCKS + (
    "remediation_performed",
    "service_action_performed",
    "network_stack_mutation",
)


class ContractError(ValueError):
    """Raised when an offline contract fails closed."""


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ContractError(f"cannot load JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ContractError(f"top-level JSON must be an object: {path}")
    return value


def load_contracts() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    allowlist = load_json(ALLOWLIST_PATH)
    request_schema = load_json(REQUEST_SCHEMA_PATH)
    evidence_schema = load_json(EVIDENCE_SCHEMA_PATH)

    if allowlist.get("status") != "inactive":
        raise ContractError("allowlist status must remain inactive")

    for field in (
        "activation_authorized",
        "implementation_present",
        "observer_installed",
        "observer_enabled",
        "observer_scheduled",
    ):
        if allowlist.get(field) is not False:
            raise ContractError(f"inactive-state control is not false: {field}")

    for field, value in allowlist.get("governance", {}).items():
        if value is not False:
            raise ContractError(f"governance control is not false: {field}")

    Draft202012Validator.check_schema(request_schema)
    Draft202012Validator.check_schema(evidence_schema)
    return allowlist, request_schema, evidence_schema


def validate_schema(instance: dict[str, Any], schema: dict[str, Any]) -> None:
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = sorted(validator.iter_errors(instance), key=lambda item: list(item.path))
    if errors:
        details = "; ".join(error.message for error in errors[:5])
        raise ContractError(f"schema validation failed: {details}")


def require_false(instance: dict[str, Any], fields: tuple[str, ...]) -> None:
    for field in fields:
        if instance.get(field) is not False:
            raise ContractError(f"{field} must be false")


def validate_timestamp_order(instance: dict[str, Any]) -> None:
    try:
        started = datetime.fromisoformat(instance["started_at"].replace("Z", "+00:00"))
        completed = datetime.fromisoformat(
            instance["completed_at"].replace("Z", "+00:00")
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise ContractError(f"invalid evidence timestamp: {exc}") from exc

    if completed < started:
        raise ContractError("completed_at precedes started_at")


def validate_operation_pair(observation_class: str, operation: str) -> None:
    allowed = CLASS_OPERATIONS.get(observation_class)
    if allowed is None or operation not in allowed:
        raise ContractError(
            f"operation {operation!r} is forbidden for class {observation_class!r}"
        )


def validate_http_target(target: str, allowlist: dict[str, Any]) -> None:
    if target not in allowlist["http"]["endpoints"]:
        raise ContractError("HTTP target is not exactly allowlisted")

    parsed = urlsplit(target)
    if (
        parsed.scheme != "http"
        or parsed.hostname not in {"127.0.0.1", "localhost"}
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
    ):
        raise ContractError("HTTP target violates loopback URL restrictions")


def validate_filesystem_target(target: str, allowlist: dict[str, Any]) -> None:
    candidate = Path(target)
    if not candidate.is_absolute():
        raise ContractError("filesystem target must be absolute")

    if ".." in candidate.parts:
        raise ContractError("filesystem target contains path traversal")

    exact_files = {Path(path) for path in allowlist["filesystem"]["exact_files"]}
    approved_roots = {
        Path(path).resolve(strict=False)
        for path in allowlist["filesystem"]["approved_roots"]
    }
    normalized = candidate.resolve(strict=False)

    if normalized in exact_files:
        return

    for root in approved_roots:
        try:
            normalized.relative_to(root)
            return
        except ValueError:
            continue

    raise ContractError("filesystem target escapes approved roots")


def validate_target(
    instance: dict[str, Any],
    allowlist: dict[str, Any],
) -> None:
    observation_class = instance["observation_class"]
    operation = instance["operation"]
    target = instance["target"]

    validate_operation_pair(observation_class, operation)

    if observation_class == "systemd":
        if operation in SYSTEMD_GLOBAL_OPERATIONS:
            if target != "system":
                raise ContractError("global systemd target must be 'system'")
        elif target not in allowlist["systemd"]["units"]:
            raise ContractError("systemd unit is not allowlisted")

    elif observation_class == "journal":
        if target not in allowlist["systemd"]["units"]:
            raise ContractError("journal unit is not allowlisted")

    elif observation_class == "socket":
        if target != "local-listening-sockets":
            raise ContractError("socket target must use the fixed local target")

    elif observation_class == "http":
        validate_http_target(target, allowlist)

    elif observation_class == "filesystem":
        validate_filesystem_target(target, allowlist)

    elif observation_class == "git":
        repository = allowlist["git"]["repository"]
        if target != repository:
            raise ContractError("Git target is not the approved repository")


def validate_limits(instance: dict[str, Any], allowlist: dict[str, Any]) -> None:
    limits = allowlist["limits"]

    if instance["timeout_seconds"] > limits["command_timeout_seconds_max"]:
        raise ContractError("timeout exceeds allowlist maximum")

    request_limit = instance.get("output_bytes_max")
    if (
        request_limit is not None
        and request_limit > limits["output_bytes_max"]
    ):
        raise ContractError("output bound exceeds allowlist maximum")

    if instance.get("journal_lines", 0) > limits["journal_lines_max"]:
        raise ContractError("journal line bound exceeds allowlist maximum")

    if (
        instance.get("journal_lookback_seconds", 0)
        > limits["journal_lookback_seconds_max"]
    ):
        raise ContractError("journal lookback exceeds allowlist maximum")

    if instance.get("output_bytes", 0) > limits["output_bytes_max"]:
        raise ContractError("evidence output exceeds allowlist maximum")


def validate_request(instance: dict[str, Any]) -> None:
    allowlist, request_schema, _ = load_contracts()
    validate_schema(instance, request_schema)
    require_false(instance, FALSE_LOCKS)
    validate_target(instance, allowlist)
    validate_limits(instance, allowlist)


def validate_evidence(instance: dict[str, Any]) -> None:
    allowlist, _, evidence_schema = load_contracts()
    validate_schema(instance, evidence_schema)
    require_false(instance, EVIDENCE_FALSE_LOCKS)
    validate_target(instance, allowlist)
    validate_limits(instance, allowlist)
    validate_timestamp_order(instance)

    if instance["policy_decision"] == "allowed_read_only":
        if instance["classification"] == "failed":
            raise ContractError("failed evidence cannot claim allowed_read_only")


def canonical_sha256(instance: dict[str, Any]) -> str:
    encoded = json.dumps(
        instance,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
