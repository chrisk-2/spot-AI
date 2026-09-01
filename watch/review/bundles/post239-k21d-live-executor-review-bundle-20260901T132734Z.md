# Post-2.39 K21D Live Installation-Only Executor Review Bundle

## Review identity

- generated at: 2026-09-01T13:27:34Z
- host: spot-core
- repository head: ab6ae8cba093074482ab3aa9209c8a9c9ed3ab5b
- reviewer: spot-worker-05
- reviewer authority: proposal_review_only
- model: qwen2.5-coder:32b
- review phase: repository live-executor implementation acceptance

## Intent

Review the hash-pinned K21D live installation-only executor candidate and its
offline validation. Determine whether it safely implements the accepted K21D
transaction design while preserving the exact accepted K21C/K21D eight-file
mapping and all Starfleet governance boundaries.

## Temporal and authority interpretation

- The earlier implementation PASS reviewed the historical dormant installer.
- This bundle reviews the later live executor candidate; it does not rewrite
  the historical result.
- The installation authorization created before live-executor review was
  revoked before use and remains unconsumed.
- No current backup or installation manifest should exist during this review.
- A fresh, single-use authorization bound to a PASS from this review is
  required before any future installation transaction.
- A future authorized transaction must verify its backup and rollback binding
  before mutation and durably consume its authorization before first mutation.
- The executor may conditionally run daemon-reload only when the installed unit
  bytes changed.
- The executor must never start, restart, enable, schedule, dispatch a request,
  or perform production observation.
- Spot Core remains sole executor. Worker-05 reviews only and cannot apply.
- Current execution_allowed and mutation_authority remain false.

## Exact review targets

- live executor: watch/observe/controlled-read-observe-install-transaction.py
- live executor SHA-256: 2b30248eb2d5fb4583c0b96003616e204978144f8c2651efc4e6a1804927e325
- disposable execution test: watch/observe/controlled-read-observe-install-transaction-execution-test.py
- execution-test SHA-256: 6810b844fd3ebcbda8290e0cf0a224169ed479cd7577080f49cc25158336b330
- live implementation validator: watch/observe/controlled-read-observe-install-transaction-implementation-validate.py
- implementation-validator SHA-256: c72b4a1c72029e7475ca3ed56cd5f2740f2a2407c5e0ba625c1d604aa5ded002

## Authority and review bindings

- construction authorization: watch/review/bundles/AUTH-POST239-K21D-LIVE-EXECUTOR-CONSTRUCTION-20260829T170427Z.json
- construction authorization SHA-256: c42eb2118c530da1f0f6b6ad4d47e5cdd50dc0c08c775ffa0d13e6de7132c5a3
- revoked installation authorization: watch/review/bundles/AUTH-POST239-K21D-INSTALLATION-20260829T163721Z.json
- revoked installation authorization SHA-256: b64054247a611e6f949f99cfaf4a275082aed5a81c457fab5f19e603edc91e1a
- revocation: watch/review/bundles/REVOKE-POST239-K21D-INSTALLATION-20260829T163721Z.json
- revocation SHA-256: ae403d76af62d60bdb03c344f8e446e6c3702c56dffd289a21e191b0547970f6
- blueprint PASS: watch/review/bundles/POST239-K21D-BLUEPRINT-PASS-20260828T150447Z.json
- blueprint PASS SHA-256: ca9b109a863369a1874cf30ac6bf295664c2b8ad50135ab2e7528146a0218b2e
- historical dormant implementation PASS: watch/review/bundles/POST239-K21D-IMPLEMENTATION-PASS-20260828T222053Z.json
- historical dormant implementation PASS SHA-256: c5836d5b38cc97895e748c8b70ceb8b7420f467b4a18a02a33c84df79ab19673
- mapping-correction PASS: watch/review/bundles/POST239-K21D-MAPPING-CORRECTION-PASS-20260829T162201Z.json
- mapping-correction PASS SHA-256: 7eda6a23447300e11ac660eb381dacf783190abb82c0cae5d38fc4a94cc172f0

## Required review findings

Worker-05 must verify all of the following:

1. Exact mapping remains the accepted ordered eight-file mapping.
2. Executor input is schema-validated and hash-bound.
3. A fresh authorization is required and single-use replay is denied.
4. Authorization consumption becomes durable before first live mutation.
5. Backup content, metadata, containment, and rollback binding are verified.
6. Destination symlinks and source, backup, or receipt tampering fail closed.
7. Partial failure invokes rollback and verifies exact restoration.
8. daemon-reload is conditional on unit-byte change only.
9. Start, restart, enablement, scheduling, request dispatch, and production
   observation remain forbidden.
10. Offline tests do not touch any live destination.
11. No current installation authority is created by this review.
12. A new review-bound installation authorization remains required.

## Current construction authorization

~~~json
{
  "schema": "starfleet.post239.k21d_live_executor_construction_authorization.v1",
  "authorization_id": "AUTH-POST239-K21D-LIVE-EXECUTOR-CONSTRUCTION-20260829T170427Z",
  "generated_at": "2026-08-29T17:04:27Z",
  "authorized_by": {
    "role": "operator",
    "identity": "ogre",
    "authority": "live_installer_construction_and_review_only"
  },
  "repository": {
    "host": "spot-core",
    "branch": "main",
    "head": "ab6ae8cba093074482ab3aa9209c8a9c9ed3ab5b",
    "required_clean_except_runtime_drift": "starfleet-ui/public/status.json"
  },
  "correlated_review": {
    "blueprint_pass_path": "watch/review/bundles/POST239-K21D-BLUEPRINT-PASS-20260828T150447Z.json",
    "blueprint_pass_sha256": "ca9b109a863369a1874cf30ac6bf295664c2b8ad50135ab2e7528146a0218b2e",
    "dormant_implementation_pass_path": "watch/review/bundles/POST239-K21D-IMPLEMENTATION-PASS-20260828T222053Z.json",
    "dormant_implementation_pass_sha256": "c5836d5b38cc97895e748c8b70ceb8b7420f467b4a18a02a33c84df79ab19673",
    "mapping_correction_pass_path": "watch/review/bundles/POST239-K21D-MAPPING-CORRECTION-PASS-20260829T162201Z.json",
    "mapping_correction_pass_sha256": "7eda6a23447300e11ac660eb381dacf783190abb82c0cae5d38fc4a94cc172f0",
    "worker05_verdict": "PASS"
  },
  "revoked_installation_authorization": {
    "record_path": "watch/review/bundles/AUTH-POST239-K21D-INSTALLATION-20260829T163721Z.json",
    "record_sha256": "b64054247a611e6f949f99cfaf4a275082aed5a81c457fab5f19e603edc91e1a",
    "revocation_path": "watch/review/bundles/REVOKE-POST239-K21D-INSTALLATION-20260829T163721Z.json",
    "revocation_sha256": "ae403d76af62d60bdb03c344f8e446e6c3702c56dffd289a21e191b0547970f6",
    "status": "REVOKED_BEFORE_USE_EXECUTOR_NOT_REVIEWED"
  },
  "fixed_repository_artifacts": [
    "watch/observe/controlled-read-observe-install-transaction.py",
    "watch/observe/controlled-read-observe-install-transaction-execution-test.py"
  ],
  "scope": {
    "repository_artifact_construction_authorized": true,
    "dormant_installer_replacement_authorized": true,
    "live_installer_construction_authorized": true,
    "rollback_implementation_authorized": true,
    "offline_fixture_execution_authorized": true,
    "adversarial_test_construction_authorized": true,
    "offline_validation_authorized": true,
    "review_bundle_creation_authorized": true,
    "worker05_review_authorized": true,
    "pass_record_creation_authorized": true,
    "commit_authorized_after_worker05_pass": false,
    "push_authorized_after_worker05_pass": false,
    "backup_creation_authorized": false,
    "installation_manifest_creation_authorized": false,
    "authorization_consumption_authorized": false,
    "system_path_installation_authorized": false,
    "daemon_reload_authorized": false,
    "activation_authorized": false,
    "enablement_authorized": false,
    "scheduling_authorized": false,
    "production_observation_authorized": false
  },
  "required_executor_controls": {
    "spot_core_only": true,
    "exact_eight_file_mapping": true,
    "transaction_schema_validation": true,
    "authorization_digest_validation": true,
    "authorization_expiry_validation": true,
    "backup_manifest_digest_validation": true,
    "rollback_binding_validation": true,
    "source_digest_validation": true,
    "destination_type_validation": true,
    "atomic_installation": true,
    "conditional_daemon_reload_only": true,
    "rollback_on_failure": true,
    "post_install_verification": true,
    "observer_must_remain_inactive": true,
    "observer_must_remain_disabled": true,
    "timer_must_remain_absent": true,
    "request_dispatch_forbidden": true,
    "production_observation_forbidden": true,
    "immutable_receipt_required": true,
    "replay_denial_required": true
  },
  "governance": {
    "spot_core_sole_authority": true,
    "worker_self_apply_allowed": false,
    "live_executor_enabled": false,
    "execution_allowed": false,
    "mutation_authority": false
  },
  "status": "AUTHORIZED_FOR_K21D_LIVE_EXECUTOR_CONSTRUCTION_AND_REVIEW_ONLY"
}
~~~

## Revocation of pre-review installation authorization

~~~json
{
  "schema": "starfleet.post239.k21d_installation_authorization_revocation.v1",
  "generated_at": "2026-08-29T17:04:27Z",
  "host": "spot-core",
  "repository_head": "ab6ae8cba093074482ab3aa9209c8a9c9ed3ab5b",
  "revoked_authorization_path": "watch/review/bundles/AUTH-POST239-K21D-INSTALLATION-20260829T163721Z.json",
  "revoked_authorization_sha256": "b64054247a611e6f949f99cfaf4a275082aed5a81c457fab5f19e603edc91e1a",
  "reason": "Reviewed K21D installer remained dormant and denied execution",
  "backup_created": false,
  "installation_manifest_created": false,
  "authorization_consumed": false,
  "installation_performed": false,
  "daemon_reload_performed": false,
  "activation_authorized": false,
  "scheduling_authorized": false,
  "production_observation_authorized": false,
  "execution_allowed": false,
  "mutation_authority": false,
  "status": "REVOKED_BEFORE_USE_EXECUTOR_NOT_REVIEWED"
}
~~~

## Prior accepted review records

### Blueprint PASS

~~~json
{
  "schema": "starfleet.post239.k21d_blueprint_review.v1",
  "generated_at": "2026-08-28T15:04:47Z",
  "reviewer": {
    "worker": "spot-worker-05",
    "model": "qwen2.5-coder:32b",
    "authority": "design_review_only"
  },
  "reviewed_bundle": "watch/review/bundles/post239-k21d-blueprint-review-bundle-20260828T140358Z.md",
  "reviewed_bundle_sha256": "86b8de3b5701f5c31a661a363b408133b63a6229de647575b42f1909fe6d07fb",
  "review": {
    "activation_authorized": false,
    "backup_defined": true,
    "backup_required": true,
    "blocking_findings": [],
    "confidence": "high",
    "daemon_reload_authorized": false,
    "exact_file_mappings_defined": true,
    "execution_allowed": false,
    "installation_transaction_design_accepted": true,
    "intent_match": "pass",
    "k21c_schema_preserved": true,
    "k21d_transaction_authorized": false,
    "mutation_authority": false,
    "notes": "The blueprint meets all the required conditions for a PASS. It defines separate stages, exactly eight fixed mappings, preserves K21C schema, requires single-use authorization, and includes rollback definitions.",
    "phase_match": "pass",
    "policy_match": "pass",
    "production_observation_authorized": false,
    "required_fixes": [],
    "rollback_defined": true,
    "scheduling_authorized": false,
    "single_use_authorization_defined": true,
    "system_path_installation_authorized": false,
    "validation_defined": true,
    "verdict": "PASS"
  },
  "installation_transaction_design_accepted": true,
  "k21d_transaction_authorized": false,
  "k21d_transaction_schema_constructed": false,
  "k21d_installer_constructed": false,
  "k21d_authorization_created": false,
  "system_path_installation_authorized": false,
  "daemon_reload_authorized": false,
  "daemon_reload_performed": false,
  "installation_performed": false,
  "activation_authorized": false,
  "scheduling_authorized": false,
  "production_observation_authorized": false,
  "execution_allowed": false,
  "mutation_authority": false
}
~~~

### Historical dormant implementation PASS

~~~json
{
  "schema": "starfleet.post239.k21d_implementation_review.v1",
  "generated_at": "2026-08-28T22:20:53Z",
  "reviewer": {
    "worker": "spot-worker-05",
    "model": "qwen2.5-coder:32b",
    "authority": "repository_implementation_review_only"
  },
  "reviewed_bundle": "watch/review/bundles/post239-k21d-implementation-review-bundle-20260828T220017Z.md",
  "reviewed_bundle_sha256": "c416193e81e86475388ff77867b114033809d757dc1b17e683dbe232b8b41494",
  "review": {
    "activation_authorized": false,
    "authorization_consumed": false,
    "backup_created_now": false,
    "blocking_findings": [],
    "confidence": "high",
    "daemon_reload_authorized": false,
    "daemon_reload_performed": false,
    "execution_allowed": false,
    "future_transaction_backup_required": true,
    "implementation_accepted": true,
    "installation_manifest_created": false,
    "installation_performed": false,
    "k21d_transaction_authorized": false,
    "mutation_authority": false,
    "notes": "The bundle meets all the required conditions and does not contradict any of the definitions provided.",
    "production_observation_authorized": false,
    "required_fixes": [],
    "rollback_defined": true,
    "scheduling_authorized": false,
    "system_path_installation_authorized": false,
    "verdict": "PASS"
  },
  "implementation_accepted": true,
  "future_transaction_backup_required": true,
  "backup_created_now": false,
  "k21d_transaction_authorized": false,
  "system_path_installation_authorized": false,
  "installation_manifest_created": false,
  "authorization_consumed": false,
  "installation_performed": false,
  "daemon_reload_authorized": false,
  "daemon_reload_performed": false,
  "activation_authorized": false,
  "scheduling_authorized": false,
  "production_observation_authorized": false,
  "execution_allowed": false,
  "mutation_authority": false
}
~~~

### Mapping-correction PASS

~~~json
{
  "schema": "starfleet.post239.k21d_mapping_correction_review.v1",
  "generated_at": "2026-08-29T16:23:16Z",
  "reviewer": {
    "worker": "spot-worker-05",
    "authority": "correction_review_only"
  },
  "reviewed_bundle": "watch/review/bundles/post239-k21d-mapping-clarification-review-bundle-20260829T162201Z.md",
  "reviewed_bundle_sha256": "431bd47e6ced9b1f09d953d524a24d9e2ff69860efaa3e4a82427c4e3bbe33b4",
  "original_correction_bundle": "watch/review/bundles/post239-k21d-mapping-correction-review-bundle-20260829T153201Z.md",
  "original_correction_bundle_sha256": "86d07c49df7a18769e6b34cc071113679283bbceb72e0c44bc6b10b858698a0d",
  "canonical_k21c_mapping_sha256": "fc8d965a5c2a963bec28f8ecca69a655b0eb22e37b08bb606e73d287d5366fe3",
  "canonical_k21d_mapping_sha256": "fc8d965a5c2a963bec28f8ecca69a655b0eb22e37b08bb606e73d287d5366fe3",
  "revocation_record": "watch/review/bundles/REVOKE-POST239-K21D-INSTALLATION-20260829T130152Z.json",
  "revocation_record_sha256": "254ed739940642221a508e8194623738743845b37f2c6805475cad77011430bb",
  "review": {
    "verdict": "PASS",
    "confidence": "high",
    "intent_match": "pass",
    "phase_match": "pass",
    "policy_match": "pass",
    "mapping_correction_accepted": true,
    "authoritative_mapping_equal": true,
    "authoritative_sources_present": true,
    "destination_modes_defined": true,
    "k21c_contract_preserved": true,
    "revocation_accepted": true,
    "invalid_authorization_consumed": false,
    "fresh_installation_authorization_required": true,
    "k21d_transaction_authorized": false,
    "system_path_installation_authorized": false,
    "backup_created": false,
    "installation_manifest_created": false,
    "installation_performed": false,
    "daemon_reload_authorized": false,
    "daemon_reload_performed": false,
    "activation_authorized": false,
    "scheduling_authorized": false,
    "production_observation_authorized": false,
    "execution_allowed": false,
    "mutation_authority": false,
    "blocking_findings": [],
    "required_fixes": [],
    "notes": "The current K21D mapping matches the authoritative K21C mapping, and all necessary checks have been passed. A fresh single-use installation authorization is required for any future installation."
  },
  "mapping_correction_accepted": true,
  "authoritative_mapping_equal": true,
  "authoritative_sources_present": true,
  "destination_modes_defined": true,
  "k21c_contract_preserved": true,
  "invalid_authorization_consumed": false,
  "fresh_installation_authorization_required": true,
  "k21d_transaction_authorized": false,
  "system_path_installation_authorized": false,
  "backup_created": false,
  "installation_manifest_created": false,
  "installation_performed": false,
  "daemon_reload_authorized": false,
  "daemon_reload_performed": false,
  "activation_authorized": false,
  "scheduling_authorized": false,
  "production_observation_authorized": false,
  "execution_allowed": false,
  "mutation_authority": false
}
~~~

## Fresh live implementation validation

~~~text
[PASS] hash-pinned live executor and exact mapping
[PASS] live executor static self-test
[PASS] disposable execution and rollback tests
[PASS] transaction-contract regression
[PASS] live paths absent and repository unchanged
pass=5 fail=0
system_path_installation_authorized=false
backup_created=false
installation_manifest_created=false
authorization_consumed=false
installation_performed=false
daemon_reload_performed=false
activation_authorized=false
scheduling_authorized=false
production_observation_authorized=false
execution_allowed=false
mutation_authority=false
RESULT: POST-2.39 K21D LIVE IMPLEMENTATION VALIDATION PASS
~~~

## Fresh disposable execution tests

~~~text
[PASS] positive installation confined to offline fixture
[PASS] denied: single-use authorization replay
[PASS] denied: source digest tamper
[PASS] denied: backup content tamper
[PASS] denied: destination symlink
[PASS] denied: post-install failure triggers rollback
[PASS] verified rollback restores exact pre-install state
[PASS] daemon-reload omitted when unit content is unchanged
[PASS] denied: expired authorization
[PASS] denied: revoked authorization
[PASS] denied: receipt collision
positive_tests=3
negative_tests=7
live_system_paths_touched=false
installation_performed=false
daemon_reload_performed=false
activation_authorized=false
execution_allowed=false
mutation_authority=false
RESULT: POST-2.39 K21D LIVE EXECUTOR OFFLINE TEST PASS
~~~

## Fresh transaction-contract regression

~~~text
[PASS] valid offline K21D transaction accepted
[PASS] rejected: unexpected field
[PASS] rejected: wrong host
[PASS] rejected: expired transaction
[PASS] rejected: review not PASS
[PASS] rejected: installation authorization false
[PASS] rejected: authorization not single-use
[PASS] rejected: authorization consumed
[PASS] rejected: backup not verified
[PASS] rejected: backup path escape
[PASS] rejected: rollback not verified
[PASS] rejected: file omitted
[PASS] rejected: source substituted
[PASS] rejected: destination substituted
[PASS] rejected: mode expanded
[PASS] rejected: unconditional daemon-reload
[PASS] rejected: service start planned
[PASS] rejected: service enablement planned
[PASS] rejected: timer installation planned
[PASS] rejected: request dispatch planned
[PASS] rejected: production observation planned
[PASS] rejected: worker self-apply
[PASS] rejected: activation authority expanded
[PASS] rejected: execution authority expanded
[PASS] rejected: mutation authority expanded
positive_tests=1
negative_tests=24
installation_manifest_created=false
backup_created=false
installation_performed=false
daemon_reload_performed=false
execution_allowed=false
mutation_authority=false
RESULT: POST-2.39 K21D FAILURE TEST PASS
~~~

## Live executor source

Path: watch/observe/controlled-read-observe-install-transaction.py

~~~python
#!/usr/bin/env python3
"""Fail-closed K21D installation-only transaction executor.

The live CLI is restricted to spot-core, the fixed repository, the reviewed
eight-file mapping, and one transaction/authorization/backup identity.  It
never starts, enables, schedules, or invokes the observer.
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
from pathlib import Path
from typing import Any, Callable, Sequence


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

LIVE_REPOSITORY = Path("/home/ogre/spot-stack")
BACKUP_BASE = Path("/mnt/collective/backups/spot-core/post239-k21d")
EVIDENCE_BASE = Path("/mnt/collective/logs/spot/actions/post239-k21d")
LOCK_PATH = Path("/run/lock/spot-post239-k21d-install.lock")
RUNTIME_REQUEST = Path("/var/lib/spot/controlled-read-observe/request.json")
RUNTIME_EVIDENCE = Path("/var/lib/spot/controlled-read-observe/evidence")
RUNTIME_DRIFT = "starfleet-ui/public/status.json"
SERVICE = "spot-controlled-read-observe.service"
TRANSACTION_VALIDATOR = Path(
    "watch/observe/controlled-read-observe-install-transaction-validate.py"
)
BACKUP_SCHEMA = "starfleet.post239.k21d_install_backup.v1"
AUTH_SCHEMA = "starfleet.post239.k21d_installation_authorization.v1"
RECEIPT_SCHEMA = "starfleet.post239.k21d_installation_receipt.v1"
CONSUMPTION_SCHEMA = "starfleet.post239.k21d_authorization_consumption.v1"
MAX_JSON_BYTES = 2 * 1024 * 1024


class ExecutionError(RuntimeError):
    """A fail-closed installation denial or transaction failure."""


@dataclass
class CommandResult:
    returncode: int
    stdout: str = ""
    stderr: str = ""


CommandRunner = Callable[[Sequence[str], Path | None], CommandResult]


@dataclass
class ExecutionContext:
    repository: Path
    system_root: Path
    lock_path: Path
    command_runner: CommandRunner
    now: Callable[[], datetime]
    hostname: Callable[[], str]
    live: bool

    def absolute(self, value: str | Path) -> Path:
        path = Path(value)
        require(path.is_absolute(), f"path is not absolute: {path}")
        if self.system_root == Path("/"):
            return path
        return self.system_root / str(path).lstrip("/")


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ExecutionError(message)


def exact_keys(value: Any, keys: set[str], label: str) -> dict[str, Any]:
    require(isinstance(value, dict), f"{label} must be an object")
    require(set(value) == keys, f"{label} fields mismatch: {sorted(set(value) ^ keys)}")
    return value


def utc_text(value: datetime | None = None) -> str:
    current = value or datetime.now(timezone.utc)
    return current.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def parse_time(value: Any, label: str) -> datetime:
    require(isinstance(value, str), f"{label} must be a string")
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ExecutionError(f"invalid {label}") from exc
    require(result.tzinfo is not None, f"{label} lacks timezone")
    return result.astimezone(timezone.utc)


def regular_lstat(path: Path, label: str) -> os.stat_result:
    try:
        info = path.lstat()
    except FileNotFoundError as exc:
        raise ExecutionError(f"{label} missing: {path}") from exc
    require(stat.S_ISREG(info.st_mode), f"{label} is not a regular file: {path}")
    require(not path.is_symlink(), f"{label} is a symlink: {path}")
    return info


def digest_file(path: Path, label: str = "file") -> str:
    regular_lstat(path, label)
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags)
    value = hashlib.sha256()
    try:
        opened = os.fstat(descriptor)
        require(stat.S_ISREG(opened.st_mode), f"{label} changed type: {path}")
        with os.fdopen(descriptor, "rb", closefd=False) as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                value.update(chunk)
    finally:
        os.close(descriptor)
    return value.hexdigest()


def read_regular_bytes(
    path: Path,
    label: str,
    *,
    maximum: int | None = None,
) -> bytes:
    regular_lstat(path, label)
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags)
    try:
        opened = os.fstat(descriptor)
        require(stat.S_ISREG(opened.st_mode), f"{label} changed type: {path}")
        if maximum is not None:
            require(opened.st_size <= maximum, f"{label} exceeds size limit")
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            total += len(chunk)
            if maximum is not None:
                require(total <= maximum, f"{label} exceeds size limit")
            chunks.append(chunk)
        closed = os.fstat(descriptor)
        require(
            (opened.st_dev, opened.st_ino, opened.st_size)
            == (closed.st_dev, closed.st_ino, closed.st_size),
            f"{label} changed while reading: {path}",
        )
        return b"".join(chunks)
    finally:
        os.close(descriptor)


def read_json(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(
            read_regular_bytes(path, label, maximum=MAX_JSON_BYTES).decode("utf-8")
        )
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ExecutionError(f"cannot parse {label}: {exc}") from exc
    require(isinstance(payload, dict), f"{label} must be an object")
    return payload


def fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def atomic_json_exclusive(path: Path, payload: dict[str, Any]) -> None:
    require(path.is_absolute(), "journal path must be absolute")
    require(path.parent.is_dir(), f"journal directory missing: {path.parent}")
    require(not os.path.lexists(path), f"journal already exists: {path}")
    data = (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode()
    descriptor, temporary_text = tempfile.mkstemp(
        prefix=f".{path.name}.", dir=path.parent
    )
    temporary = Path(temporary_text)
    linked = False
    try:
        os.fchmod(descriptor, 0o600)
        os.write(descriptor, data)
        os.fsync(descriptor)
        os.close(descriptor)
        descriptor = -1
        os.link(temporary, path, follow_symlinks=False)
        linked = True
        fsync_directory(path.parent)
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
        if not linked and os.path.lexists(path):
            raise ExecutionError(f"exclusive journal collision: {path}")


def default_runner(arguments: Sequence[str], cwd: Path | None) -> CommandResult:
    completed = subprocess.run(
        list(arguments),
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=120,
    )
    return CommandResult(completed.returncode, completed.stdout, completed.stderr)


def run_checked(
    context: ExecutionContext,
    arguments: Sequence[str],
    label: str,
    *,
    cwd: Path | None = None,
) -> CommandResult:
    result = context.command_runner(arguments, cwd)
    require(
        result.returncode == 0,
        f"{label} failed: {(result.stderr or result.stdout).strip()}",
    )
    return result


def load_transaction_validator(repository: Path) -> Any:
    path = repository / TRANSACTION_VALIDATOR
    regular_lstat(path, "transaction validator")
    spec = importlib.util.spec_from_file_location("k21d_transaction_validator", path)
    require(spec is not None and spec.loader is not None, "cannot load validator")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate_repository(context: ExecutionContext, head: str) -> None:
    if not context.live:
        return
    require(context.repository.resolve() == LIVE_REPOSITORY, "wrong repository")
    require(context.hostname() == "spot-core", "wrong execution host")
    require(os.geteuid() == 0, "live installation requires root")
    checks = (
        (["git", "branch", "--show-current"], "main", "wrong branch"),
        (["git", "rev-parse", "HEAD"], head, "repository head mismatch"),
        (["git", "rev-parse", "origin/main"], head, "origin/main mismatch"),
    )
    for command, expected, label in checks:
        result = run_checked(context, command, label, cwd=context.repository)
        require(result.stdout.strip() == expected, label)
    staged = run_checked(
        context,
        ["git", "diff", "--cached", "--name-only"],
        "staged-diff check",
        cwd=context.repository,
    )
    require(not staged.stdout.strip(), "staged changes present")
    drift = run_checked(
        context,
        ["git", "diff", "--name-only"],
        "worktree check",
        cwd=context.repository,
    )
    require(drift.stdout.strip() == RUNTIME_DRIFT, "unexpected worktree drift")


def expected_mapping(transaction: dict[str, Any]) -> list[dict[str, Any]]:
    files = transaction.get("files")
    require(isinstance(files, list) and len(files) == 8, "wrong file count")
    result: list[dict[str, Any]] = []
    for index, ((source, destination, mode), item) in enumerate(
        zip(FILE_MAP, files), start=1
    ):
        require(isinstance(item, dict), f"file {index} is not an object")
        require(item.get("source") == source, f"file {index} source mismatch")
        require(
            item.get("destination") == destination,
            f"file {index} destination mismatch",
        )
        require(item.get("mode") == mode, f"file {index} mode mismatch")
        result.append(
            {
                "source": source,
                "source_sha256": item.get("source_sha256"),
                "destination": destination,
                "mode": mode,
                "owner": "root",
                "group": "root",
            }
        )
    return result


def validate_authorization(
    context: ExecutionContext,
    transaction: dict[str, Any],
    authorization_path: Path,
    authorization_sha256: str,
) -> dict[str, Any]:
    authorization = read_json(authorization_path, "installation authorization")
    require(digest_file(authorization_path) == authorization_sha256, "authorization digest mismatch")
    exact_keys(
        authorization,
        {
            "schema",
            "authorization_id",
            "generated_at",
            "expires_at",
            "authorized_by",
            "repository",
            "correlated_reviews",
            "fixed_mappings",
            "scope",
            "replay_control",
            "governance",
            "status",
        },
        "installation authorization",
    )
    operator = transaction["operator_authorization"]
    require(authorization.get("schema") == AUTH_SCHEMA, "wrong authorization schema")
    require(
        authorization.get("authorization_id") == operator["authorization_id"],
        "authorization ID mismatch",
    )
    require(authorization.get("status") == "AUTHORIZED_FOR_SINGLE_K21D_INSTALLATION_ONLY", "authorization status invalid")

    generated = parse_time(authorization.get("generated_at"), "authorization generated_at")
    expires = parse_time(authorization.get("expires_at"), "authorization expires_at")
    now = context.now().astimezone(timezone.utc)
    require(generated < expires, "authorization is not forward-expiring")
    require(generated <= now < expires, "authorization expired or not yet valid")
    require(parse_time(transaction["expires_at"], "transaction expires_at") <= expires, "transaction outlives authorization")

    authorized_by = exact_keys(
        authorization.get("authorized_by"),
        {"role", "identity", "authority"},
        "authorized_by",
    )
    require(authorized_by["role"] == "operator", "authorization role mismatch")
    require(isinstance(authorized_by["identity"], str) and authorized_by["identity"], "authorization identity missing")
    require(authorized_by["authority"] == "single_use_installation_only", "authorization authority mismatch")

    repository = exact_keys(
        authorization.get("repository"),
        {"host", "branch", "head", "required_clean_except_runtime_drift"},
        "authorization repository",
    )
    require(repository.get("host") == "spot-core", "authorization host mismatch")
    require(repository.get("branch") == "main", "authorization branch mismatch")
    require(repository.get("head") == transaction["repository_head"], "authorization head mismatch")
    require(repository.get("required_clean_except_runtime_drift") == RUNTIME_DRIFT, "authorization drift boundary mismatch")

    reviews = exact_keys(
        authorization.get("correlated_reviews"),
        {
            "blueprint_pass_path",
            "blueprint_pass_sha256",
            "implementation_pass_path",
            "implementation_pass_sha256",
            "mapping_correction_pass_path",
            "mapping_correction_pass_sha256",
            "live_executor_pass_path",
            "live_executor_pass_sha256",
            "worker05_verdict",
        },
        "correlated reviews",
    )
    require(reviews["worker05_verdict"] == "PASS", "Worker-05 review not PASS")
    for prefix in (
        "blueprint_pass",
        "implementation_pass",
        "mapping_correction_pass",
        "live_executor_pass",
    ):
        relative = reviews[f"{prefix}_path"]
        expected_digest = reviews[f"{prefix}_sha256"]
        require(isinstance(relative, str) and relative.startswith("watch/review/bundles/"), f"bad {prefix} path")
        review_path = (context.repository / relative).resolve()
        require(context.repository in review_path.parents, f"{prefix} path escapes repository")
        require(digest_file(review_path, prefix) == expected_digest, f"{prefix} digest mismatch")
    live_review = read_json(
        (context.repository / reviews["live_executor_pass_path"]).resolve(),
        "live executor PASS",
    )
    require(live_review.get("verdict") == "PASS", "live executor verdict not PASS")
    require(live_review.get("live_executor_accepted") is True, "live executor not accepted")
    require(live_review.get("system_path_installation_authorized") is False, "review record improperly authorizes installation")

    mappings = authorization.get("fixed_mappings")
    require(mappings == expected_mapping(transaction), "authorization mapping mismatch")

    scope = exact_keys(
        authorization.get("scope"),
        {
            "k21d_transaction_authorized",
            "backup_creation_authorized",
            "installation_manifest_creation_authorized",
            "system_path_installation_authorized",
            "installation_receipt_creation_authorized",
            "authorization_consumption_authorized",
            "daemon_reload_if_unit_changed_authorized",
            "rollback_execution_authorized",
            "rollback_stop_if_unexpected_active_authorized",
            "unconditional_daemon_reload_authorized",
            "activation_authorized",
            "enablement_authorized",
            "scheduling_authorized",
            "request_dispatch_authorized",
            "production_observation_authorized",
            "service_action_authorized",
            "remediation_authorized",
        },
        "authorization scope",
    )
    for field in (
        "k21d_transaction_authorized",
        "backup_creation_authorized",
        "installation_manifest_creation_authorized",
        "system_path_installation_authorized",
        "installation_receipt_creation_authorized",
        "authorization_consumption_authorized",
        "daemon_reload_if_unit_changed_authorized",
        "rollback_execution_authorized",
        "rollback_stop_if_unexpected_active_authorized",
    ):
        require(scope.get(field) is True, f"required authority absent: {field}")
    for field in (
        "unconditional_daemon_reload_authorized",
        "activation_authorized",
        "enablement_authorized",
        "scheduling_authorized",
        "request_dispatch_authorized",
        "production_observation_authorized",
        "service_action_authorized",
        "remediation_authorized",
    ):
        require(scope.get(field) is False, f"unsafe authority present: {field}")

    replay = exact_keys(
        authorization.get("replay_control"),
        {"single_use", "consumed", "installation_completed", "rollback_completed"},
        "replay control",
    )
    require(replay.get("single_use") is True, "authorization is not single-use")
    require(replay.get("consumed") is False, "authorization already consumed")
    require(replay.get("installation_completed") is False, "authorization already completed")

    governance = exact_keys(
        authorization.get("governance"),
        {
            "spot_core_sole_authority",
            "worker_self_apply_allowed",
            "live_executor_enabled",
            "execution_allowed",
            "mutation_authority",
        },
        "authorization governance",
    )
    require(governance.get("spot_core_sole_authority") is True, "Spot Core authority missing")
    for field in (
        "worker_self_apply_allowed",
        "live_executor_enabled",
        "execution_allowed",
        "mutation_authority",
    ):
        require(governance.get(field) is False, f"unsafe governance state: {field}")

    review_dir = context.repository / "watch/review/bundles"
    for revocation_path in review_dir.glob("REVOKE-POST239-K21D-INSTALLATION-*.json"):
        revocation = read_json(revocation_path, "authorization revocation")
        if (
            revocation.get("revoked_authorization_path")
            == operator["record_path"]
            or revocation.get("revoked_authorization_sha256")
            == authorization_sha256
        ):
            raise ExecutionError(f"authorization revoked: {revocation_path.name}")
    return authorization


def validate_backup(
    context: ExecutionContext,
    transaction: dict[str, Any],
    authorization: dict[str, Any],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    backup = transaction["backup"]
    expected_manifest = BACKUP_BASE / f"{backup['manifest_id']}.json"
    require(Path(backup["manifest_path"]) == expected_manifest, "backup manifest path mismatch")
    physical_manifest = context.absolute(expected_manifest)
    require(physical_manifest.resolve() == physical_manifest, "backup manifest path traverses a symlink")
    manifest = read_json(physical_manifest, "backup manifest")
    exact_keys(
        manifest,
        {
            "schema",
            "manifest_id",
            "generated_at",
            "host",
            "repository_head",
            "authorization_id",
            "authorization_sha256",
            "binding_id",
            "files",
            "verified",
            "status",
        },
        "backup manifest",
    )
    require(digest_file(physical_manifest) == backup["manifest_sha256"], "backup manifest digest mismatch")
    require(manifest.get("schema") == BACKUP_SCHEMA, "wrong backup schema")
    require(manifest.get("manifest_id") == backup["manifest_id"], "backup ID mismatch")
    require(manifest.get("binding_id") == backup["binding_id"], "backup binding mismatch")
    require(manifest.get("host") == "spot-core", "backup host mismatch")
    require(manifest.get("repository_head") == transaction["repository_head"], "backup repository mismatch")
    require(manifest.get("authorization_id") == authorization["authorization_id"], "backup authorization mismatch")
    require(manifest.get("authorization_sha256") == transaction["operator_authorization"]["record_sha256"], "backup authorization digest mismatch")
    require(manifest.get("verified") is True, "backup is not verified")
    require(manifest.get("status") == "VERIFIED_PREINSTALL_BACKUP", "backup status invalid")
    entries = manifest.get("files")
    require(isinstance(entries, list) and len(entries) == 8, "backup file count mismatch")

    verified: list[dict[str, Any]] = []
    backup_dir = BACKUP_BASE / f"{backup['manifest_id']}-files"
    for index, (entry, transaction_file, mapping) in enumerate(
        zip(entries, transaction["files"], FILE_MAP), start=1
    ):
        source, destination, _mode = mapping
        exact_keys(
            entry,
            {
                "source",
                "destination",
                "destination_preexisting",
                "destination_type_before",
                "backup_path",
                "backup_sha256",
                "mode_before",
                "uid_before",
                "gid_before",
            },
            f"backup entry {index}",
        )
        require(entry.get("source") == source, f"backup source mismatch at {index}")
        require(entry.get("destination") == destination, f"backup destination mismatch at {index}")
        require(entry.get("destination_preexisting") is transaction_file["destination_preexisting"], f"backup state mismatch at {index}")
        require(entry.get("destination_type_before") == transaction_file["destination_type_before"], f"backup type mismatch at {index}")
        require(entry.get("backup_sha256") == transaction_file["backup_sha256"], f"backup digest binding mismatch at {index}")
        if transaction_file["destination_preexisting"]:
            expected_path = backup_dir / f"{index:02d}-{Path(destination).name}.backup"
            require(entry.get("backup_path") == str(expected_path), f"backup path mismatch at {index}")
            physical = context.absolute(expected_path)
            require(physical.resolve() == physical, f"backup path traverses a symlink at {index}")
            require(digest_file(physical, f"backup file {index}") == entry["backup_sha256"], f"backup content mismatch at {index}")
            require(
                isinstance(entry["mode_before"], str)
                and len(entry["mode_before"]) == 4
                and all(character in "01234567" for character in entry["mode_before"]),
                f"backup mode invalid at {index}",
            )
            require(isinstance(entry["uid_before"], int) and entry["uid_before"] >= 0, f"backup uid invalid at {index}")
            require(isinstance(entry["gid_before"], int) and entry["gid_before"] >= 0, f"backup gid invalid at {index}")
        else:
            require(entry.get("backup_path") is None, f"unexpected backup path at {index}")
            require(entry.get("backup_sha256") is None, f"unexpected backup digest at {index}")
            require(entry.get("mode_before") is None, f"unexpected backup mode at {index}")
            require(entry.get("uid_before") is None, f"unexpected backup uid at {index}")
            require(entry.get("gid_before") is None, f"unexpected backup gid at {index}")
        verified.append(entry)
    return manifest, verified


def destination_state(
    context: ExecutionContext,
    item: dict[str, Any],
    backup: dict[str, Any],
    index: int,
) -> None:
    destination = context.absolute(item["destination"])
    exists = os.path.lexists(destination)
    if item["destination_preexisting"]:
        require(exists, f"preexisting destination missing at {index}")
        info = regular_lstat(destination, f"destination {index}")
        require(digest_file(destination) == item["backup_sha256"], f"destination changed after backup at {index}")
        require(stat.S_IMODE(info.st_mode) == int(backup["mode_before"], 8), f"destination mode changed after backup at {index}")
        require(info.st_uid == backup["uid_before"], f"destination uid changed after backup at {index}")
        require(info.st_gid == backup["gid_before"], f"destination gid changed after backup at {index}")
    else:
        require(not exists, f"destination unexpectedly exists at {index}")


def secure_parent(context: ExecutionContext, destination: Path, created: list[Path]) -> None:
    allowed = {
        context.absolute("/usr/local/lib/spot/observe"),
        context.absolute("/etc/spot/observe"),
        context.absolute("/etc/systemd/system"),
    }
    parent = destination.parent
    require(parent in allowed, f"destination parent not allowed: {parent}")
    if not parent.exists():
        require(parent.parent.is_dir(), f"fixed parent base missing: {parent.parent}")
        require(parent.parent.resolve() == parent.parent, f"fixed parent base is unsafe: {parent.parent}")
        parent.mkdir(mode=0o755)
        if context.live:
            os.chown(parent, 0, 0)
        created.append(parent)
        fsync_directory(parent.parent)
    info = parent.lstat()
    require(stat.S_ISDIR(info.st_mode) and not parent.is_symlink(), f"unsafe destination parent: {parent}")
    require(parent.resolve() == parent, f"destination parent traverses symlink: {parent}")
    require(info.st_mode & 0o022 == 0, f"writable destination parent: {parent}")
    if context.live:
        require(info.st_uid == 0 and info.st_gid == 0, f"destination parent not root-owned: {parent}")


def atomic_install(
    context: ExecutionContext,
    source: Path,
    destination: Path,
    mode: str,
    created_directories: list[Path],
    expected_sha256: str,
    uid: int = 0,
    gid: int = 0,
) -> None:
    secure_parent(context, destination, created_directories)
    data = read_regular_bytes(source, "atomic installation source")
    require(hashlib.sha256(data).hexdigest() == expected_sha256, "atomic source digest mismatch")
    descriptor, temporary_text = tempfile.mkstemp(prefix=".spot-k21d-", dir=destination.parent)
    temporary = Path(temporary_text)
    try:
        os.fchmod(descriptor, int(mode, 8))
        if context.live:
            os.fchown(descriptor, uid, gid)
        os.write(descriptor, data)
        os.fsync(descriptor)
        os.close(descriptor)
        descriptor = -1
        os.replace(temporary, destination)
        fsync_directory(destination.parent)
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def verify_installed(context: ExecutionContext, transaction: dict[str, Any]) -> None:
    for index, item in enumerate(transaction["files"], start=1):
        destination = context.absolute(item["destination"])
        info = regular_lstat(destination, f"installed destination {index}")
        require(digest_file(destination) == item["source_sha256"], f"installed digest mismatch at {index}")
        require(stat.S_IMODE(info.st_mode) == int(item["mode"], 8), f"installed mode mismatch at {index}")
        if context.live:
            require(info.st_uid == 0 and info.st_gid == 0, f"installed ownership mismatch at {index}")


def snapshot_path(path: Path) -> str:
    value = hashlib.sha256()
    if not os.path.lexists(path):
        value.update(b"absent")
        return value.hexdigest()
    root_info = path.lstat()
    if stat.S_ISREG(root_info.st_mode):
        value.update(b"file\0" + digest_file(path).encode())
        return value.hexdigest()
    if stat.S_ISLNK(root_info.st_mode):
        value.update(b"link\0" + os.readlink(path).encode())
        return value.hexdigest()
    require(stat.S_ISDIR(root_info.st_mode), f"unsupported runtime path type: {path}")
    value.update(b"directory\0")
    for child in sorted(path.rglob("*"), key=lambda item: str(item.relative_to(path))):
        relative = str(child.relative_to(path)).encode()
        info = child.lstat()
        value.update(relative + b"\0" + oct(stat.S_IMODE(info.st_mode)).encode() + b"\0")
        if stat.S_ISREG(info.st_mode):
            value.update(digest_file(child).encode())
        elif stat.S_ISLNK(info.st_mode):
            value.update(b"link:" + os.readlink(child).encode())
        elif stat.S_ISDIR(info.st_mode):
            value.update(b"directory")
        else:
            value.update(f"special:{stat.S_IFMT(info.st_mode)}".encode())
    return value.hexdigest()


def running_services(context: ExecutionContext) -> str:
    result = run_checked(
        context,
        ["systemctl", "list-units", "--type=service", "--state=running", "--no-legend", "--no-pager", "--plain"],
        "running-service snapshot",
    )
    lines = [line for line in result.stdout.splitlines() if SERVICE not in line]
    return "\n".join(sorted(line.strip() for line in lines if line.strip()))


def assert_service_safe(context: ExecutionContext, *, unit_must_exist: bool) -> dict[str, Any]:
    active = context.command_runner(["systemctl", "is-active", SERVICE], None)
    active_state = active.stdout.strip()
    require(active_state in {"inactive", "unknown"}, f"observer is not inactive: {active_state}")
    if unit_must_exist:
        require(active_state == "inactive", "installed observer unit is not inactive")
    enabled = context.command_runner(["systemctl", "is-enabled", SERVICE], None)
    enabled_state = enabled.stdout.strip()
    safe_enabled = {"disabled", "static", "not-found", "unknown"}
    require(enabled_state in safe_enabled, f"observer is enabled: {enabled_state}")
    if unit_must_exist:
        require(enabled_state in {"disabled", "static"}, "installed observer unit enablement state unsafe")
    main_pid = context.command_runner(["systemctl", "show", SERVICE, "--property=MainPID", "--value"], None)
    require(main_pid.returncode in {0, 1, 3, 4}, "cannot inspect observer MainPID")
    require(main_pid.stdout.strip() in {"", "0"}, "observer process exists")
    timers = context.command_runner(
        ["systemctl", "list-unit-files", "spot-controlled-read-observe*.timer", "--no-legend", "--no-pager"],
        None,
    )
    require(timers.returncode == 0, "cannot inspect observer timers")
    require(not timers.stdout.strip(), "controlled-read-observe timer registered")
    for base in ("/etc/systemd/system", "/usr/lib/systemd/system", "/lib/systemd/system"):
        physical = context.absolute(base)
        if physical.is_dir():
            require(not list(physical.glob("*controlled-read-observe*.timer")), "controlled-read-observe timer file exists")
    return {"active_state": active_state, "enabled_state": enabled_state, "main_pid": main_pid.stdout.strip() or "0"}


def run_offline_regressions(context: ExecutionContext) -> list[str]:
    commands = (
        ["python3", "watch/observe/controlled_read_observe_validation_v1.py"],
        ["python3", "watch/observe/controlled-read-observe-replay-bounds-validate.py"],
        ["python3", "watch/observe/controlled-read-observe-install-validate.py"],
        ["python3", "watch/observe/controlled-read-observe-install-transaction-failure-test.py"],
    )
    passed: list[str] = []
    for command in commands:
        run_checked(context, command, f"offline regression {command[1]}", cwd=context.repository)
        passed.append(command[1])
    return passed


def rollback_installation(
    context: ExecutionContext,
    transaction: dict[str, Any],
    authorization: dict[str, Any],
    backup_entries: list[dict[str, Any]],
    installed_indices: list[int],
    created_directories: list[Path],
    unit_changed: bool,
) -> dict[str, Any]:
    failures: list[str] = []
    restored: list[str] = []
    active = context.command_runner(["systemctl", "is-active", SERVICE], None)
    if active.stdout.strip() == "active":
        try:
            require(
                authorization["scope"]["rollback_stop_if_unexpected_active_authorized"] is True,
                "rollback stop authority absent",
            )
            run_checked(
                context,
                ["systemctl", "stop", SERVICE],
                "rollback stop of unexpectedly active observer",
            )
        except ExecutionError as exc:
            failures.append(str(exc))
    installed_set = set(installed_indices)
    for index in reversed(range(1, len(transaction["files"]) + 1)):
        if index not in installed_set:
            continue
        item = transaction["files"][index - 1]
        backup = backup_entries[index - 1]
        destination = context.absolute(item["destination"])
        try:
            if item["destination_preexisting"]:
                backup_path = context.absolute(backup["backup_path"])
                require(digest_file(backup_path) == item["backup_sha256"], f"rollback backup mismatch at {index}")
                atomic_install(
                    context,
                    backup_path,
                    destination,
                    backup["mode_before"],
                    created_directories,
                    item["backup_sha256"],
                    backup["uid_before"],
                    backup["gid_before"],
                )
                require(digest_file(destination) == item["backup_sha256"], f"rollback restore mismatch at {index}")
            else:
                if os.path.lexists(destination):
                    regular_lstat(destination, f"rollback destination {index}")
                    require(digest_file(destination) == item["source_sha256"], f"rollback refuses changed destination at {index}")
                    destination.unlink()
                    fsync_directory(destination.parent)
                require(not os.path.lexists(destination), f"rollback removal failed at {index}")
            restored.append(item["destination"])
        except (OSError, ExecutionError) as exc:
            failures.append(str(exc))
    if unit_changed:
        try:
            run_checked(context, ["systemctl", "daemon-reload"], "rollback daemon-reload")
        except ExecutionError as exc:
            failures.append(str(exc))
    for directory in reversed(created_directories):
        try:
            directory.rmdir()
            fsync_directory(directory.parent)
        except OSError:
            pass
    try:
        assert_service_safe(context, unit_must_exist=False)
    except ExecutionError as exc:
        failures.append(str(exc))
    return {"restored": restored, "failures": failures, "succeeded": not failures}


def consumption_and_receipt_paths(context: ExecutionContext, transaction_id: str) -> tuple[Path, Path]:
    evidence = context.absolute(EVIDENCE_BASE)
    return (
        evidence / f"{transaction_id}.consumption.json",
        evidence / f"{transaction_id}.receipt.json",
    )


def execute_transaction(context: ExecutionContext, transaction_path: Path) -> dict[str, Any]:
    context.repository = context.repository.resolve()
    transaction = read_json(transaction_path, "installation transaction")
    validator = load_transaction_validator(context.repository)
    try:
        validator.validate_transaction(transaction, context.repository, verify_references=True)
    except Exception as exc:  # validator owns its exception type
        raise ExecutionError(f"transaction validation failed: {exc}") from exc

    require(transaction.get("host") == "spot-core", "transaction host mismatch")
    require(context.hostname() == "spot-core", "wrong execution host")
    now = context.now().astimezone(timezone.utc)
    require(parse_time(transaction["generated_at"], "transaction generated_at") <= now, "transaction not yet valid")
    require(now < parse_time(transaction["expires_at"], "transaction expires_at"), "transaction expired")
    validate_repository(context, transaction["repository_head"])

    expected_transaction = context.absolute(EVIDENCE_BASE) / f"{transaction['transaction_id']}.json"
    require(transaction_path.resolve() == expected_transaction, "transaction path is not canonical")
    transaction_sha256 = digest_file(transaction_path)

    operator = transaction["operator_authorization"]
    authorization_path = context.repository / operator["record_path"]
    authorization = validate_authorization(
        context,
        transaction,
        authorization_path,
        operator["record_sha256"],
    )
    _backup_manifest, backup_entries = validate_backup(context, transaction, authorization)

    for index, item in enumerate(transaction["files"], start=1):
        source = context.repository / item["source"]
        require(digest_file(source, f"source {index}") == item["source_sha256"], f"source digest mismatch at {index}")
        destination_state(context, item, backup_entries[index - 1], index)

    consumption_path, receipt_path = consumption_and_receipt_paths(context, transaction["transaction_id"])
    require(not os.path.lexists(consumption_path), "authorization consumption record already exists")
    require(not os.path.lexists(receipt_path), "installation receipt already exists")

    request_before = snapshot_path(context.absolute(RUNTIME_REQUEST))
    evidence_before = snapshot_path(context.absolute(RUNTIME_EVIDENCE))
    services_before = running_services(context)
    service_before = assert_service_safe(context, unit_must_exist=False)

    lock_path = context.lock_path
    require(lock_path.parent.is_dir(), f"lock directory missing: {lock_path.parent}")
    lock_flags = os.O_RDWR | os.O_CREAT
    if hasattr(os, "O_NOFOLLOW"):
        lock_flags |= os.O_NOFOLLOW
    lock_descriptor = os.open(lock_path, lock_flags, 0o600)
    try:
        fcntl.flock(lock_descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError as exc:
        os.close(lock_descriptor)
        raise ExecutionError("another K21D installation transaction holds the lock") from exc

    installed_indices: list[int] = []
    created_directories: list[Path] = []
    unit_changed = False
    daemon_reload_performed = False
    consumption_written = False
    try:
        require(not os.path.lexists(consumption_path), "authorization consumed while waiting for lock")
        require(not os.path.lexists(receipt_path), "receipt appeared while waiting for lock")
        consumption = {
            "schema": CONSUMPTION_SCHEMA,
            "transaction_id": transaction["transaction_id"],
            "transaction_sha256": transaction_sha256,
            "authorization_id": authorization["authorization_id"],
            "authorization_path": operator["record_path"],
            "authorization_sha256": operator["record_sha256"],
            "consumed_at": utc_text(now),
            "single_use": True,
            "consumed_before_mutation": True,
            "status": "CONSUMED_FOR_ONE_INSTALLATION_ATTEMPT",
        }
        atomic_json_exclusive(consumption_path, consumption)
        consumption_written = True

        unit_item = transaction["files"][-1]
        unit_destination = context.absolute(unit_item["destination"])
        unit_changed = (
            not unit_item["destination_preexisting"]
            or digest_file(unit_destination) != unit_item["source_sha256"]
        )

        for index, item in enumerate(transaction["files"], start=1):
            source = context.repository / item["source"]
            destination = context.absolute(item["destination"])
            atomic_install(
                context,
                source,
                destination,
                item["mode"],
                created_directories,
                item["source_sha256"],
            )
            installed_indices.append(index)
            require(digest_file(destination) == item["source_sha256"], f"immediate install verification failed at {index}")

        if unit_changed:
            run_checked(context, ["systemctl", "daemon-reload"], "conditional daemon-reload")
            daemon_reload_performed = True

        verify_installed(context, transaction)
        unit_physical = context.absolute("/etc/systemd/system/spot-controlled-read-observe.service")
        run_checked(context, ["systemd-analyze", "verify", str(unit_physical)], "unit verification")
        service_after = assert_service_safe(context, unit_must_exist=True)
        regressions = run_offline_regressions(context)
        require(snapshot_path(context.absolute(RUNTIME_REQUEST)) == request_before, "runtime request changed")
        require(snapshot_path(context.absolute(RUNTIME_EVIDENCE)) == evidence_before, "runtime observation evidence changed")
        require(running_services(context) == services_before, "unrelated running-service state changed")

        receipt = {
            "schema": RECEIPT_SCHEMA,
            "transaction_id": transaction["transaction_id"],
            "transaction_sha256": transaction_sha256,
            "authorization_id": authorization["authorization_id"],
            "authorization_sha256": operator["record_sha256"],
            "backup_manifest_id": transaction["backup"]["manifest_id"],
            "backup_manifest_sha256": transaction["backup"]["manifest_sha256"],
            "backup_binding_id": transaction["backup"]["binding_id"],
            "rollback_binding_id": transaction["rollback"]["binding_id"],
            "repository_head": transaction["repository_head"],
            "completed_at": utc_text(context.now()),
            "installed_files": [
                {
                    "destination": item["destination"],
                    "sha256": item["source_sha256"],
                    "mode": item["mode"],
                    "owner": "root",
                    "group": "root",
                }
                for item in transaction["files"]
            ],
            "service_state_before": service_before,
            "service_state_after": service_after,
            "unit_changed": unit_changed,
            "daemon_reload_performed": daemon_reload_performed,
            "offline_regressions": regressions,
            "request_state_unchanged": True,
            "runtime_evidence_unchanged": True,
            "unrelated_running_services_unchanged": True,
            "activation_performed": False,
            "enablement_performed": False,
            "scheduling_performed": False,
            "production_observation_performed": False,
            "execution_allowed": False,
            "mutation_authority": False,
            "outcome": "INSTALLED_DORMANT",
        }
        atomic_json_exclusive(receipt_path, receipt)
        return receipt
    except (OSError, ExecutionError) as exc:
        rollback = rollback_installation(
            context,
            transaction,
            authorization,
            backup_entries,
            installed_indices,
            created_directories,
            unit_changed and bool(installed_indices),
        ) if installed_indices else {"restored": [], "failures": [], "succeeded": True}
        failure_receipt = {
            "schema": RECEIPT_SCHEMA,
            "transaction_id": transaction["transaction_id"],
            "transaction_sha256": transaction_sha256,
            "authorization_id": authorization["authorization_id"],
            "authorization_sha256": operator["record_sha256"],
            "failed_at": utc_text(context.now()),
            "failure": str(exc),
            "authorization_consumed": consumption_written,
            "rollback": rollback,
            "daemon_reload_performed_before_failure": daemon_reload_performed,
            "activation_performed": False,
            "enablement_performed": False,
            "scheduling_performed": False,
            "production_observation_performed": False,
            "execution_allowed": False,
            "mutation_authority": False,
            "outcome": "ROLLED_BACK" if rollback["succeeded"] else "ROLLBACK_FAILED",
        }
        if consumption_written and not os.path.lexists(receipt_path):
            try:
                atomic_json_exclusive(receipt_path, failure_receipt)
            except (OSError, ExecutionError) as journal_exc:
                raise ExecutionError(f"{exc}; rollback={rollback}; receipt failure={journal_exc}") from journal_exc
        raise ExecutionError(f"{exc}; rollback_succeeded={rollback['succeeded']}") from exc
    finally:
        fcntl.flock(lock_descriptor, fcntl.LOCK_UN)
        os.close(lock_descriptor)


def offline_self_test() -> None:
    require(len(FILE_MAP) == 8, "mapping count changed")
    require(len({entry[0] for entry in FILE_MAP}) == 8, "duplicate source")
    require(len({entry[1] for entry in FILE_MAP}) == 8, "duplicate destination")
    require(FILE_MAP[-1][1] == "/etc/systemd/system/spot-controlled-read-observe.service", "unit destination changed")
    for _source, destination, mode in FILE_MAP:
        require(destination.startswith(("/usr/local/lib/spot/observe/", "/etc/spot/observe/", "/etc/systemd/system/")), "destination escaped fixed roots")
        require(mode in {"0755", "0644"}, "unexpected destination mode")


def main() -> int:
    parser = argparse.ArgumentParser(description="K21D installation-only executor")
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--offline-self-test", action="store_true")
    action.add_argument("--execute", action="store_true")
    parser.add_argument("--transaction", type=Path)
    parser.add_argument("--repository", type=Path, default=LIVE_REPOSITORY)
    args = parser.parse_args()

    if args.offline_self_test:
        require(args.transaction is None, "offline self-test takes no transaction")
        try:
            offline_self_test()
        except ExecutionError as exc:
            print(f"[DENY] K21D executor self-test failed: {exc}", file=sys.stderr)
            return 2
        print("[PASS] K21D live executor static self-test")
        print("installation_performed=false")
        print("daemon_reload_performed=false")
        print("activation_authorized=false")
        print("execution_allowed=false")
        print("mutation_authority=false")
        return 0

    if args.transaction is None:
        parser.error("--execute requires --transaction")

    context = ExecutionContext(
        repository=args.repository,
        system_root=Path("/"),
        lock_path=LOCK_PATH,
        command_runner=default_runner,
        now=lambda: datetime.now(timezone.utc),
        hostname=socket.gethostname,
        live=True,
    )
    try:
        receipt = execute_transaction(context, args.transaction.resolve())
    except (OSError, ExecutionError) as exc:
        print(f"[DENY] K21D installation failed closed: {exc}", file=sys.stderr)
        print("activation_performed=false", file=sys.stderr)
        print("enablement_performed=false", file=sys.stderr)
        print("scheduling_performed=false", file=sys.stderr)
        print("production_observation_performed=false", file=sys.stderr)
        print("execution_allowed=false", file=sys.stderr)
        print("mutation_authority=false", file=sys.stderr)
        return 2

    print("[PASS] K21D installation-only transaction complete")
    print(f"transaction_id={receipt['transaction_id']}")
    print("observer_installed=true")
    print("observer_active=false")
    print("observer_enabled=false")
    print("observer_scheduled=false")
    print("production_observation_performed=false")
    print("execution_allowed=false")
    print("mutation_authority=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
~~~

## Disposable execution-test source

Path: watch/observe/controlled-read-observe-install-transaction-execution-test.py

~~~python
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
            "single-use authorization replay",
            lambda: module.execute_transaction(fixture.context(), fixture.transaction_path),
            module,
        )
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
    source_tamper(module)
    backup_tamper(module)
    symlink_destination(module)
    rollback_after_failure(module)
    unchanged_unit_no_reload(module)
    expired_authorization(module)
    revoked_authorization(module)
    receipt_collision(module)
    print("positive_tests=3")
    print("negative_tests=7")
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
~~~

## Live implementation-validator source

Path: watch/observe/controlled-read-observe-install-transaction-implementation-validate.py

~~~python
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
~~~

## Current safety state

- system_path_installation_authorized=false
- backup_created=false
- installation_manifest_created=false
- authorization_consumed=false
- installation_performed=false
- daemon_reload_authorized=false
- daemon_reload_performed=false
- activation_authorized=false
- enablement_authorized=false
- scheduling_authorized=false
- production_observation_authorized=false
- execution_allowed=false
- mutation_authority=false
