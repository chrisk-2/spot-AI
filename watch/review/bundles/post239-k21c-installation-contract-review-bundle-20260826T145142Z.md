# Post-2.39 K21C Installation-Contract Implementation Review

## Review instruction

Worker-05 must return PASS, FIX, or NO for the source-level K21C
installation-contract artifacts.

Do not authorize system-path installation, daemon-reload, activation,
scheduling, production observation, service actions, remediation,
execution, or mutation.

## Repository identity

- repository head: `11850954445808e74e6c46007ce4c7961fcb04f2`
- generated UTC: `2026-08-26T14:51:43Z`

## Correlated governance

- blueprint PASS: `watch/review/bundles/POST239-K21C-BLUEPRINT-PASS-20260826T141952Z.json`
- blueprint PASS SHA-256: `64bdc0aa6289d65aadf28e417cddb75b4e1e3eef227595d449ddb3487142a519`
- construction authorization: `watch/review/bundles/AUTH-POST239-K21C-INSTALLATION-CONSTRUCTION-20260826T142510Z.json`
- construction authorization SHA-256: `6e301b283e405cf195600a53925e691d9e6dd36522b6454e61906bde5c3c6186`

## Required PASS conditions

- unit has no enablement or timer surface
- unit uses one fixed runner, request, and evidence path
- offline fixture flag is absent from the unit
- network and capability access are restricted
- evidence directory is the only writable service path
- installation manifest requires exactly eight fixed files
- source hashes, destination mappings, modes, owners, and groups are enforced
- system-path installation requires separate authorization
- verified backup and rollback bindings are mandatory
- rollback preserves evidence and touches only fixed destinations
- activation and scheduling remain false
- production observation remains unauthorized
- execution_allowed remains false
- mutation_authority remains false

## Current state

- installation artifacts constructed: true
- system-path installation authorized: false
- installation performed: false
- daemon-reload performed: false
- activation authorized: false
- observer installed: false
- observer enabled: false
- observer scheduled: false
- production observation performed: false
- execution_allowed: false
- mutation_authority: false

## Source identities

- `watch/observe/POST239-K21C-INSTALLATION-ACTIVATION-BLUEPRINT.md`: `638197a47fcb4841d61ed16e3fce0ced05b28ed3973a295ae196fd0bc9aec564`
- `watch/observe/controlled-read-observe.service`: `083b27278ec0d502e2e6f4865ba4fa6c495bbe6d00c5d20485297e6c95dc14b7`
- `watch/observe/controlled-read-observe-install-validate.py`: `46af59c951637d4a76d764c67afda85649c9f02472b85fbebb3a96c106f81ee9`
- `watch/observe/controlled-read-observe-install-rollback.md`: `415faeafe79c69a6f7215e53f7e46776d0571ee9655afd1d71dc214dfa17515c`
- `watch/observe/controlled-read-observe-install-manifest-schema-v1.json`: `46f7bddf1d2432470effee5c8f8dd1b06be399b8761cd0e86f0e0654bf34f648`
- `watch/observe/controlled-read-observe-install-manifest-validate.py`: `0595c1cc2f01db9ce66365d14b6b7001c8dd5811bb2ec310623f7301a759b90b`
- `watch/observe/controlled-read-observe-install-manifest-failure-test.py`: `d4cd9a538e5b7deace2ca5a25af15645854ac255950a614acf42cc090decb1fc`

## K21A validation

```text
[PASS] baseline request and evidence accepted
[PASS] canonical request digest is deterministic
[PASS] canonical digest is key-order independent
[PASS] material request change alters digest
[PASS] byte-equivalent identity replay is deterministic
[PASS] rejected: same observation_id with changed payload
[PASS] rejected: same request_id with changed payload
[PASS] request minimum timeout accepted
[PASS] request maximum timeout accepted
[PASS] request minimum output bound accepted
[PASS] request maximum output bound accepted
[PASS] zero-byte evidence accepted
[PASS] maximum bounded evidence accepted
[PASS] maximum journal bounds accepted
[PASS] rejected: timeout below minimum
[PASS] rejected: timeout above maximum
[PASS] rejected: output bound below minimum
[PASS] rejected: output bound above maximum
[PASS] rejected: evidence timeout below minimum
[PASS] rejected: evidence timeout above maximum
[PASS] rejected: evidence output below minimum
[PASS] rejected: evidence output above maximum
[PASS] rejected: journal lines below minimum
[PASS] rejected: journal lines above maximum
[PASS] rejected: journal lookback below minimum
[PASS] rejected: journal lookback above maximum
deterministic_digest_tests=3
replay_tests=2
collision_tests=2
positive_bound_tests=7
negative_bound_tests=12
observer_implemented=true
observation_attempted=false
execution_attempted=false
execution_allowed=false
mutation_authority=false
live_executor_enabled=false
[PASS] complete K21A offline suite
```

## K21B validation

```text
[PASS] production execution surfaces absent
[PASS] default production path denied fail-closed
[PASS] offline fixture produced schema-valid evidence
[PASS] changed replay evidence rejected
[PASS] non-allowlisted service rejected without evidence write
pass=4 fail=0
observer_installed=false
observer_enabled=false
observer_scheduled=false
production_observation_performed=false
service_action_performed=false
execution_allowed=false
mutation_authority=false
RESULT: POST-2.39 K21B VALIDATION PASS
```

## K21C installation-contract validation

```text
[PASS] required installation sources present
[PASS] unit is fixed-path, hardened, and non-enableable
[PASS] runner remains dormant and replay-safe
[PASS] allowlist remains inactive and non-authoritative
[PASS] request, evidence, and install schemas fail closed
[PASS] blueprint fixes the complete installation boundary
[PASS] rollback and manifest validation toolchain complete
pass=7 fail=0
installation_artifacts_valid=true
system_path_installation_authorized=false
installation_performed=false
daemon_reload_performed=false
activation_authorized=false
observer_installed=false
observer_enabled=false
observer_scheduled=false
production_observation_performed=false
execution_allowed=false
mutation_authority=false
RESULT: POST-2.39 K21C INSTALL CONTRACT VALIDATION PASS
```

## K21C manifest adversarial validation

```text
[PASS] complete valid offline manifest accepted
[PASS] rejected: unexpected top-level field
[PASS] rejected: invalid timestamp
[PASS] rejected: wrong host
[PASS] rejected: system-path authorization false
[PASS] rejected: authorization path escape
[PASS] rejected: review verdict not PASS
[PASS] rejected: backup not verified
[PASS] rejected: backup binding not verified
[PASS] rejected: backup path outside fixed root
[PASS] rejected: rollback not defined
[PASS] rejected: rollback binding not verified
[PASS] rejected: file omitted
[PASS] rejected: destination substitution
[PASS] rejected: source hash mismatch
[PASS] rejected: source mode expansion
[PASS] rejected: service activation planned
[PASS] rejected: timer installation planned
[PASS] rejected: observer enabled
[PASS] rejected: observer scheduled
[PASS] rejected: worker self-apply enabled
[PASS] rejected: activation authority expanded
[PASS] rejected: production observation authority expanded
[PASS] rejected: execution authority expanded
[PASS] rejected: mutation authority expanded
[PASS] missing correlated artifacts fail closed
positive_tests=1
negative_tests=25
installation_manifest_created=false
backup_artifact_created=false
installation_performed=false
activation_authorized=false
observer_installed=false
observer_enabled=false
observer_scheduled=false
production_observation_performed=false
execution_allowed=false
mutation_authority=false
RESULT: POST-2.39 K21C MANIFEST FAILURE TEST PASS
```

## Source: watch/observe/POST239-K21C-INSTALLATION-ACTIVATION-BLUEPRINT.md

# Post-2.39 K21C Controlled Read/Observe Installation and Activation Blueprint

## Status

DESIGN AND REVIEW ONLY

This blueprint does not authorize installation, activation, scheduling,
production observation, service actions, remediation, or mutation.

## Purpose

Define the exact promotion boundary between the accepted K21B dormant source
implementation and a future supervised, read-only production observation.

## Locked governance

- Spot Core remains the sole policy and execution authority.
- Worker self-apply remains prohibited.
- Worker-05 remains proposal/review only.
- `execution_allowed=false`
- `mutation_authority=false`
- `live_executor_enabled=false`
- `service_action_allowed=false`
- `remediation_allowed=false`
- `network_mutation_allowed=false`
- `remote_execution_allowed=false`
- Installation does not imply activation.
- Activation does not authorize remediation or mutation.
- A timer must not be installed during the first supervised observation.

## Promotion blocks

### K21C-1 — Blueprint review

Scope:

- review this installation and activation blueprint;
- verify exact paths, identities, boundaries, and rollback;
- perform no installation or production observation.

Exit gate:

- Worker-05 returns structured PASS;
- operator separately authorizes installation-only construction.

### K21C-2 — Installation-only construction

Repository artifacts to be constructed after authorization:

- `watch/observe/controlled-read-observe.service`
- `watch/observe/controlled-read-observe-install-validate.py`
- `watch/observe/controlled-read-observe-install-rollback.md`
- installation manifest schema and offline validator

Installation targets:

- runner:
  `/usr/local/lib/spot/observe/controlled-read-observe.py`
- shared validation module:
  `/usr/local/lib/spot/observe/controlled_read_observe_validation_v1.py`
- request validator:
  `/usr/local/lib/spot/observe/controlled-read-observe-request-validate.py`
- evidence validator:
  `/usr/local/lib/spot/observe/controlled-read-observe-evidence-validate.py`
- allowlist:
  `/etc/spot/observe/controlled-read-observe-allowlist-v1.json`
- request schema:
  `/etc/spot/observe/controlled-read-observe-request-schema-v1.json`
- evidence schema:
  `/etc/spot/observe/controlled-read-observe-evidence-schema-v1.json`
- systemd unit:
  `/etc/systemd/system/spot-controlled-read-observe.service`

Installation-only state:

- files may be installed only after separate authorization;
- the unit remains disabled and inactive;
- no timer is installed;
- no request is dispatched;
- no production evidence is created;
- `observer_installed=true` may be recorded only after identity verification;
- `observer_enabled=false`;
- `observer_scheduled=false`;
- `activation_authorized=false`.

### K21C-3 — First supervised observation

The first production observation requires another Worker-05 PASS and a new,
explicit operator authorization.

Exact first target:

- host: `spot-core`
- observation class: `systemd`
- operation: `systemd_show`
- target: `spot-remediation-fixture.service`
- execution mode: supervised one-shot
- timer or recurring schedule: forbidden

The observation may read only the fixed systemd properties already allowed by
the committed contracts. It must not start, stop, restart, reload, enable,
disable, mask, unmask, or otherwise change any service.

## Service design

Proposed unit identity:

- `spot-controlled-read-observe.service`
- `Type=oneshot`
- no `[Install]` section
- no automatic restart
- no timer dependency
- no network dependency
- fixed executable and configuration paths
- request supplied through one fixed root-owned request path
- evidence written beneath one fixed root-owned evidence directory

Required hardening:

- `User=root`
- `Group=root`
- `NoNewPrivileges=true`
- `PrivateTmp=true`
- `ProtectSystem=strict`
- `ProtectHome=true`
- empty capability bounding set
- `RestrictSUIDSGID=true`
- `LockPersonality=true`
- `MemoryDenyWriteExecute=true`
- filesystem write access limited to the evidence directory
- command timeout bounded by the committed allowlist

Root is required only for bounded read access. It does not grant mutation
authority.

## Runtime paths

Proposed request path:

`/var/lib/spot/controlled-read-observe/request.json`

Proposed evidence root:

`/var/lib/spot/controlled-read-observe/evidence`

Proposed immutable archive root:

`/mnt/collective/logs/spot/actions/post239-observe`

Requirements:

- request file must be root-owned and mode `0600`;
- runtime directory must be root-owned and mode `0700`;
- evidence files must use exclusive creation;
- existing evidence must never be overwritten;
- observation and request identities must be replay-safe;
- evidence must be schema-valid before acceptance;
- output remains bounded by the committed policy;
- secrets and credentials remain prohibited.

## Scheduling policy

K21C does not authorize recurring scheduling.

A future timer design requires its own review and authorization after the
first supervised one-shot observation passes.

Until then:

- timer unit absent;
- observer disabled;
- observer unscheduled;
- no automatic production observation.

## Backup requirements

Before installation, create and verify a backup manifest covering every
existing installation target.

For a missing destination, record:

- `missing_source=true`;
- intended installation path;
- reviewed source hash.

Installation is forbidden unless the backup manifest and binding validate.

## Rollback boundary

Rollback may affect only the K21C installation targets.

Rollback must:

1. stop only the observer unit if it is unexpectedly active;
2. restore every previously existing file from verified backup;
3. remove only files recorded as newly installed;
4. run `systemctl daemon-reload` only if the unit file changed;
5. verify the observer is absent or inactive, disabled, and unscheduled;
6. preserve all evidence and journals;
7. verify no unrelated service state changed.

Rollback execution requires explicit authority or may run automatically only
inside a separately reviewed installation transaction whose verification
fails.

## Required installation verification

- installed hashes equal reviewed source hashes;
- installed ownership and modes match the manifest;
- unit parses successfully;
- unit is inactive;
- unit is disabled;
- no timer exists;
- no request was dispatched;
- no production evidence was created;
- K21A and K21B offline regressions still pass;
- `execution_allowed=false`;
- `mutation_authority=false`.

## Required first-observation evidence

A future supervised observation receipt must correlate:

- operator authorization;
- Worker-05 PASS;
- reviewed bundle and SHA-256;
- repository commit;
- installation manifest;
- backup and rollback bindings;
- request digest;
- observation ID;
- evidence digest;
- exact target and operation;
- timeout and output bounds;
- validation result;
- final outcome.

## Explicitly forbidden by this blueprint

- installation without a separate authorization;
- enabling or scheduling the observer;
- timer creation during the first observation;
- arbitrary shell or command execution;
- arbitrary systemd properties;
- arbitrary host or service selection;
- remote execution;
- authenticated HTTP access;
- redirects or arbitrary URLs;
- service mutation;
- process signaling;
- package or configuration mutation;
- credential collection;
- remediation;
- production observation before separate authorization;
- widening `execution_allowed` or `mutation_authority`.

## Current state

- K21B implementation: accepted
- K21B implementation present: true
- K21C blueprint present: true after commit
- installation authorized: false
- observer installed: false
- observer enabled: false
- observer scheduled: false
- activation authorized: false
- production observation authorized: false
- execution allowed: false
- mutation authority: false

## Source: watch/observe/controlled-read-observe.service

```ini
[Unit]
Description=Spot Controlled Read Observe Lane
Documentation=file:///home/ogre/spot-stack/watch/observe/POST239-K21C-INSTALLATION-ACTIVATION-BLUEPRINT.md
ConditionPathExists=/usr/local/lib/spot/observe/controlled-read-observe.py
ConditionPathExists=/usr/local/lib/spot/observe/controlled_read_observe_validation_v1.py
ConditionPathExists=/etc/spot/observe/controlled-read-observe-allowlist-v1.json
ConditionPathExists=/var/lib/spot/controlled-read-observe/request.json

[Service]
Type=oneshot
User=root
Group=root

ExecStart=/usr/bin/python3 /usr/local/lib/spot/observe/controlled-read-observe.py --request /var/lib/spot/controlled-read-observe/request.json --evidence-dir /var/lib/spot/controlled-read-observe/evidence

TimeoutStartSec=20s
StandardOutput=journal
StandardError=journal

NoNewPrivileges=true
PrivateTmp=true
PrivateDevices=true
PrivateNetwork=true
ProtectSystem=strict
ProtectHome=true
ProtectKernelTunables=true
ProtectKernelModules=true
ProtectKernelLogs=true
ProtectControlGroups=true
ProtectClock=true
ProtectHostname=true
ProtectProc=invisible
ProcSubset=pid
RestrictSUIDSGID=true
LockPersonality=true
MemoryDenyWriteExecute=true
RestrictRealtime=true
RestrictNamespaces=true
RemoveIPC=true

CapabilityBoundingSet=
AmbientCapabilities=
RestrictAddressFamilies=AF_UNIX
SystemCallArchitectures=native
UMask=0077

ReadOnlyPaths=/etc/spot/observe
ReadOnlyPaths=/var/lib/spot/controlled-read-observe/request.json
ReadWritePaths=/var/lib/spot/controlled-read-observe/evidence
```

## Source: watch/observe/controlled-read-observe-install-validate.py

```python
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
        "system-path installation is not authorized",
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
        "system-path authorization false",
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
```

## Source: watch/observe/controlled-read-observe-install-rollback.md

# Post-2.39 K21C Controlled Read/Observe Installation Rollback

## Status

ROLLBACK DESIGN ONLY

This document defines rollback boundaries and validation requirements. It does
not authorize installation, rollback execution, daemon-reload, activation,
scheduling, production observation, or service mutation.

## Fixed installation targets

Rollback is restricted to these exact destinations:

1. `/usr/local/lib/spot/observe/controlled-read-observe.py`
2. `/usr/local/lib/spot/observe/controlled_read_observe_validation_v1.py`
3. `/usr/local/lib/spot/observe/controlled-read-observe-request-validate.py`
4. `/usr/local/lib/spot/observe/controlled-read-observe-evidence-validate.py`
5. `/etc/spot/observe/controlled-read-observe-allowlist-v1.json`
6. `/etc/spot/observe/controlled-read-observe-request-schema-v1.json`
7. `/etc/spot/observe/controlled-read-observe-evidence-schema-v1.json`
8. `/etc/systemd/system/spot-controlled-read-observe.service`

Runtime paths are:

- `/var/lib/spot/controlled-read-observe/request.json`
- `/var/lib/spot/controlled-read-observe/evidence`

Evidence and archived receipts must never be deleted or overwritten by
rollback.

## Required pre-install backup

Before any future installation:

- create one immutable backup directory;
- inspect every fixed destination;
- copy every existing regular file while preserving its contents;
- calculate SHA-256 for every backup;
- record `missing_source=true` for every absent destination;
- write a machine-readable backup manifest;
- validate the backup manifest;
- bind the backup manifest to the reviewed source bundle;
- bind this rollback design to the same reviewed source bundle.

No verified backup and binding means no installation.

## Rollback trigger conditions

A separately authorized installation transaction must halt and enter rollback
if any of these conditions occur:

- source hash mismatch;
- destination hash mismatch;
- unexpected destination type;
- ownership or mode mismatch;
- unit parsing failure;
- observer active after installation;
- observer enabled after installation;
- observer scheduled after installation;
- timer unit detected;
- request dispatched;
- production evidence created;
- offline regression failure;
- journal or receipt write failure;
- unrelated service state change;
- authority flag expansion.

## Rollback sequence

Rollback execution, if separately authorized, must perform these operations in
order:

1. Record the rollback request and correlated installation identity.
2. Confirm Spot Core is the executing host.
3. Confirm the backup manifest and bindings validate.
4. Confirm the rollback target set exactly matches the fixed destination list.
5. If the observer is unexpectedly active, stop only
   `spot-controlled-read-observe.service`.
6. For each destination with `missing_source=false`, restore only the verified
   backup corresponding to that destination.
7. For each destination with `missing_source=true`, remove only the file
   recorded as newly installed by the installation receipt.
8. Run `systemctl daemon-reload` only if the systemd unit destination changed.
9. Do not delete the runtime evidence directory.
10. Do not delete or overwrite any review, authorization, backup, journal,
    receipt, or archive record.
11. Perform the rollback verification checks.
12. Append the final rollback outcome to immutable evidence.

No wildcard, recursive deletion, shell expansion, arbitrary path, arbitrary
service, or remote execution is permitted.

## Required rollback verification

After rollback:

- every restored destination SHA-256 equals its recorded backup SHA-256;
- every destination originally absent is absent again;
- `spot-controlled-read-observe.service` is inactive;
- `spot-controlled-read-observe.service` is disabled;
- no controlled-read-observe timer exists;
- no observer process remains;
- no production request was dispatched;
- no production observation occurred;
- runtime evidence remains preserved;
- unrelated service state is unchanged;
- K21A offline validation passes;
- K21B offline validation passes;
- K21C installation-contract validation passes against repository source;
- `execution_allowed=false`;
- `mutation_authority=false`.

## Rollback evidence

The immutable rollback receipt must contain:

- rollback ID;
- installation ID;
- operator authorization ID;
- Worker-05 review record and SHA-256;
- reviewed bundle and SHA-256;
- repository commit;
- backup manifest ID and SHA-256;
- backup binding ID;
- rollback binding ID;
- exact destination list;
- before and after hashes;
- service state before and after;
- whether daemon-reload was performed;
- validation results;
- final outcome;
- rollback failure details, if any.

## Fail-closed outcome

If backup validation, restoration, verification, or journaling fails:

- stop the rollback transaction;
- report `ROLLBACK_BLOCKED` or `ROLLBACK_FAILED`;
- do not report success;
- do not widen authority;
- leave the observer inactive, disabled, and unscheduled whenever safely
  possible;
- require operator intervention.

## Current authority

- installation artifact construction authorized: true
- system-path installation authorized: false
- rollback execution authorized: false
- daemon-reload authorized: false
- activation authorized: false
- scheduling authorized: false
- production observation authorized: false
- observer installed: false
- observer enabled: false
- observer scheduled: false
- execution allowed: false
- mutation authority: false

## Source: watch/observe/controlled-read-observe-install-manifest-schema-v1.json

```json
{
  "$id": "urn:starfleet:spot:controlled-read-observe-install-manifest:v1",
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "additionalProperties": false,
  "properties": {
    "authorization": {
      "additionalProperties": false,
      "properties": {
        "authorization_id": {
          "minLength": 8,
          "type": "string"
        },
        "record_path": {
          "pattern": "^watch/review/bundles/AUTH-POST239-K21C-INSTALLATION-[A-Za-z0-9._:-]+\\.json$",
          "type": "string"
        },
        "record_sha256": {
          "pattern": "^[a-f0-9]{64}$",
          "type": "string"
        },
        "system_path_installation_authorized": {
          "const": true
        }
      },
      "required": [
        "authorization_id",
        "record_path",
        "record_sha256",
        "system_path_installation_authorized"
      ],
      "type": "object"
    },
    "backup": {
      "additionalProperties": false,
      "properties": {
        "backup_binding_id": {
          "minLength": 8,
          "type": "string"
        },
        "backup_binding_verified": {
          "const": true
        },
        "backup_manifest_id": {
          "minLength": 8,
          "type": "string"
        },
        "backup_manifest_path": {
          "pattern": "^/mnt/collective/backups/spot-core/post239-k21c/[A-Za-z0-9._:/-]+\\.json$",
          "type": "string"
        },
        "backup_manifest_sha256": {
          "pattern": "^[a-f0-9]{64}$",
          "type": "string"
        },
        "backup_verified": {
          "const": true
        }
      },
      "required": [
        "backup_manifest_id",
        "backup_manifest_path",
        "backup_manifest_sha256",
        "backup_verified",
        "backup_binding_id",
        "backup_binding_verified"
      ],
      "type": "object"
    },
    "files": {
      "items": {
        "additionalProperties": false,
        "properties": {
          "destination": {
            "enum": [
              "/usr/local/lib/spot/observe/controlled-read-observe.py",
              "/usr/local/lib/spot/observe/controlled_read_observe_validation_v1.py",
              "/usr/local/lib/spot/observe/controlled-read-observe-request-validate.py",
              "/usr/local/lib/spot/observe/controlled-read-observe-evidence-validate.py",
              "/etc/spot/observe/controlled-read-observe-allowlist-v1.json",
              "/etc/spot/observe/controlled-read-observe-request-schema-v1.json",
              "/etc/spot/observe/controlled-read-observe-evidence-schema-v1.json",
              "/etc/systemd/system/spot-controlled-read-observe.service"
            ]
          },
          "destination_preexisting": {
            "type": "boolean"
          },
          "group": {
            "const": "root"
          },
          "mode": {
            "enum": [
              "0644",
              "0755"
            ]
          },
          "owner": {
            "const": "root"
          },
          "sha256": {
            "pattern": "^[a-f0-9]{64}$",
            "type": "string"
          },
          "source": {
            "enum": [
              "watch/observe/controlled-read-observe.py",
              "watch/observe/controlled_read_observe_validation_v1.py",
              "watch/observe/controlled-read-observe-request-validate.py",
              "watch/observe/controlled-read-observe-evidence-validate.py",
              "watch/observe/controlled-read-observe-allowlist-v1.json",
              "watch/observe/controlled-read-observe-request-schema-v1.json",
              "watch/observe/controlled-read-observe-evidence-schema-v1.json",
              "watch/observe/controlled-read-observe.service"
            ]
          }
        },
        "required": [
          "source",
          "destination",
          "sha256",
          "mode",
          "owner",
          "group",
          "destination_preexisting"
        ],
        "type": "object"
      },
      "maxItems": 8,
      "minItems": 8,
      "type": "array",
      "uniqueItems": true
    },
    "generated_at": {
      "format": "date-time",
      "type": "string"
    },
    "governance": {
      "additionalProperties": false,
      "properties": {
        "activation_authorized": {
          "const": false
        },
        "execution_allowed": {
          "const": false
        },
        "live_executor_enabled": {
          "const": false
        },
        "mutation_authority": {
          "const": false
        },
        "production_observation_authorized": {
          "const": false
        },
        "scheduling_authorized": {
          "const": false
        },
        "spot_core_sole_authority": {
          "const": true
        },
        "worker_self_apply_allowed": {
          "const": false
        }
      },
      "required": [
        "spot_core_sole_authority",
        "worker_self_apply_allowed",
        "activation_authorized",
        "scheduling_authorized",
        "production_observation_authorized",
        "live_executor_enabled",
        "execution_allowed",
        "mutation_authority"
      ],
      "type": "object"
    },
    "host": {
      "const": "spot-core"
    },
    "manifest_id": {
      "pattern": "^INSTALL-POST239-K21C-[A-Za-z0-9._:-]{8,128}$",
      "type": "string"
    },
    "planned_service_state": {
      "additionalProperties": false,
      "properties": {
        "daemon_reload_planned": {
          "const": true
        },
        "observer_enabled": {
          "const": false
        },
        "observer_scheduled": {
          "const": false
        },
        "service_activation_planned": {
          "const": false
        },
        "timer_installation_planned": {
          "const": false
        }
      },
      "required": [
        "daemon_reload_planned",
        "service_activation_planned",
        "timer_installation_planned",
        "observer_enabled",
        "observer_scheduled"
      ],
      "type": "object"
    },
    "repository_head": {
      "pattern": "^[a-f0-9]{40}$",
      "type": "string"
    },
    "review": {
      "additionalProperties": false,
      "properties": {
        "review_pass_path": {
          "pattern": "^watch/review/bundles/POST239-K21C-[A-Za-z0-9._:-]+-PASS-[A-Za-z0-9._:-]+\\.json$",
          "type": "string"
        },
        "review_pass_sha256": {
          "pattern": "^[a-f0-9]{64}$",
          "type": "string"
        },
        "verdict": {
          "const": "PASS"
        }
      },
      "required": [
        "review_pass_path",
        "review_pass_sha256",
        "verdict"
      ],
      "type": "object"
    },
    "rollback": {
      "additionalProperties": false,
      "properties": {
        "rollback_binding_id": {
          "minLength": 8,
          "type": "string"
        },
        "rollback_binding_verified": {
          "const": true
        },
        "rollback_defined": {
          "const": true
        },
        "rollback_document": {
          "const": "watch/observe/controlled-read-observe-install-rollback.md"
        },
        "rollback_document_sha256": {
          "pattern": "^[a-f0-9]{64}$",
          "type": "string"
        }
      },
      "required": [
        "rollback_document",
        "rollback_document_sha256",
        "rollback_defined",
        "rollback_binding_id",
        "rollback_binding_verified"
      ],
      "type": "object"
    },
    "runtime": {
      "additionalProperties": false,
      "properties": {
        "evidence_directory": {
          "const": "/var/lib/spot/controlled-read-observe/evidence"
        },
        "evidence_directory_mode": {
          "const": "0700"
        },
        "request_file": {
          "const": "/var/lib/spot/controlled-read-observe/request.json"
        },
        "request_file_mode": {
          "const": "0600"
        },
        "runtime_owner": {
          "const": "root"
        }
      },
      "required": [
        "request_file",
        "request_file_mode",
        "evidence_directory",
        "evidence_directory_mode",
        "runtime_owner"
      ],
      "type": "object"
    },
    "schema": {
      "const": "spot_controlled_read_observe_install_manifest_v1"
    },
    "status": {
      "const": "READY_FOR_SEPARATELY_AUTHORIZED_INSTALLATION"
    }
  },
  "required": [
    "schema",
    "manifest_id",
    "generated_at",
    "host",
    "repository_head",
    "authorization",
    "review",
    "backup",
    "rollback",
    "files",
    "runtime",
    "planned_service_state",
    "governance",
    "status"
  ],
  "title": "Spot Controlled Read Observe Installation Manifest v1",
  "type": "object"
}
```

## Source: watch/observe/controlled-read-observe-install-manifest-validate.py

```python
#!/usr/bin/env python3
"""Validate a K21C controlled read/observe installation manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

SCHEMA = "spot_controlled_read_observe_install_manifest_v1"
STATUS = "READY_FOR_SEPARATELY_AUTHORIZED_INSTALLATION"

FILE_MAP = {
    "watch/observe/controlled-read-observe.py": (
        "/usr/local/lib/spot/observe/controlled-read-observe.py",
        "0755",
    ),
    "watch/observe/controlled_read_observe_validation_v1.py": (
        "/usr/local/lib/spot/observe/"
        "controlled_read_observe_validation_v1.py",
        "0755",
    ),
    "watch/observe/controlled-read-observe-request-validate.py": (
        "/usr/local/lib/spot/observe/"
        "controlled-read-observe-request-validate.py",
        "0755",
    ),
    "watch/observe/controlled-read-observe-evidence-validate.py": (
        "/usr/local/lib/spot/observe/"
        "controlled-read-observe-evidence-validate.py",
        "0755",
    ),
    "watch/observe/controlled-read-observe-allowlist-v1.json": (
        "/etc/spot/observe/controlled-read-observe-allowlist-v1.json",
        "0644",
    ),
    "watch/observe/controlled-read-observe-request-schema-v1.json": (
        "/etc/spot/observe/"
        "controlled-read-observe-request-schema-v1.json",
        "0644",
    ),
    "watch/observe/controlled-read-observe-evidence-schema-v1.json": (
        "/etc/spot/observe/"
        "controlled-read-observe-evidence-schema-v1.json",
        "0644",
    ),
    "watch/observe/controlled-read-observe.service": (
        "/etc/systemd/system/spot-controlled-read-observe.service",
        "0644",
    ),
}

TOP_LEVEL = {
    "schema",
    "manifest_id",
    "generated_at",
    "host",
    "repository_head",
    "authorization",
    "review",
    "backup",
    "rollback",
    "files",
    "runtime",
    "planned_service_state",
    "governance",
    "status",
}

SHA_PATTERN = re.compile(r"^[a-f0-9]{64}$")
HEAD_PATTERN = re.compile(r"^[a-f0-9]{40}$")
MANIFEST_PATTERN = re.compile(
    r"^INSTALL-POST239-K21C-[A-Za-z0-9._:-]{8,128}$"
)
AUTH_PATH_PATTERN = re.compile(
    r"^watch/review/bundles/"
    r"AUTH-POST239-K21C-INSTALLATION-[A-Za-z0-9._:-]+\.json$"
)
REVIEW_PATH_PATTERN = re.compile(
    r"^watch/review/bundles/"
    r"POST239-K21C-[A-Za-z0-9._:-]+-PASS-[A-Za-z0-9._:-]+\.json$"
)
BACKUP_PATH_PATTERN = re.compile(
    r"^/mnt/collective/backups/spot-core/post239-k21c/"
    r"[A-Za-z0-9._:/-]+\.json$"
)


class ManifestError(ValueError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ManifestError(message)


def exact_keys(value: Any, keys: set[str], label: str) -> dict[str, Any]:
    require(isinstance(value, dict), f"{label} must be an object")
    actual = set(value)
    require(actual == keys, f"{label} fields mismatch: {sorted(actual ^ keys)}")
    return value


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_manifest(
    manifest: dict[str, Any],
    repository: Path,
    verify_references: bool = True,
) -> None:
    exact_keys(manifest, TOP_LEVEL, "manifest")

    require(manifest["schema"] == SCHEMA, "bad schema")
    require(
        isinstance(manifest["manifest_id"], str)
        and MANIFEST_PATTERN.fullmatch(manifest["manifest_id"]) is not None,
        "bad manifest_id",
    )
    require(isinstance(manifest["generated_at"], str), "bad generated_at")
    try:
        datetime.fromisoformat(
            manifest["generated_at"].replace("Z", "+00:00")
        )
    except ValueError as exc:
        raise ManifestError("bad generated_at") from exc

    require(manifest["host"] == "spot-core", "bad host")
    require(
        isinstance(manifest["repository_head"], str)
        and HEAD_PATTERN.fullmatch(manifest["repository_head"]) is not None,
        "bad repository_head",
    )
    require(manifest["status"] == STATUS, "bad status")

    authorization = exact_keys(
        manifest["authorization"],
        {
            "authorization_id",
            "record_path",
            "record_sha256",
            "system_path_installation_authorized",
        },
        "authorization",
    )
    require(
        isinstance(authorization["authorization_id"], str)
        and len(authorization["authorization_id"]) >= 8,
        "bad authorization_id",
    )
    require(
        AUTH_PATH_PATTERN.fullmatch(authorization["record_path"]) is not None,
        "bad authorization record path",
    )
    require(
        authorization["system_path_installation_authorized"] is True,
        "system-path installation is not authorized",
    )
    require(
        SHA_PATTERN.fullmatch(authorization["record_sha256"]) is not None,
        "bad authorization record SHA-256",
    )

    review = exact_keys(
        manifest["review"],
        {"review_pass_path", "review_pass_sha256", "verdict"},
        "review",
    )
    require(
        REVIEW_PATH_PATTERN.fullmatch(review["review_pass_path"]) is not None,
        "bad review record path",
    )
    require(review["verdict"] == "PASS", "review verdict is not PASS")
    require(
        SHA_PATTERN.fullmatch(review["review_pass_sha256"]) is not None,
        "bad review SHA-256",
    )

    backup = exact_keys(
        manifest["backup"],
        {
            "backup_manifest_id",
            "backup_manifest_path",
            "backup_manifest_sha256",
            "backup_verified",
            "backup_binding_id",
            "backup_binding_verified",
        },
        "backup",
    )
    require(
        isinstance(backup["backup_manifest_id"], str)
        and len(backup["backup_manifest_id"]) >= 8,
        "bad backup manifest ID",
    )
    require(
        BACKUP_PATH_PATTERN.fullmatch(backup["backup_manifest_path"])
        is not None,
        "bad backup manifest path",
    )
    require(
        isinstance(backup["backup_binding_id"], str)
        and len(backup["backup_binding_id"]) >= 8,
        "bad backup binding ID",
    )
    require(backup["backup_verified"] is True, "backup is not verified")
    require(
        backup["backup_binding_verified"] is True,
        "backup binding is not verified",
    )
    require(
        SHA_PATTERN.fullmatch(backup["backup_manifest_sha256"]) is not None,
        "bad backup manifest SHA-256",
    )

    rollback = exact_keys(
        manifest["rollback"],
        {
            "rollback_document",
            "rollback_document_sha256",
            "rollback_defined",
            "rollback_binding_id",
            "rollback_binding_verified",
        },
        "rollback",
    )
    require(
        rollback["rollback_document"]
        == "watch/observe/controlled-read-observe-install-rollback.md",
        "unexpected rollback document",
    )
    require(
        isinstance(rollback["rollback_binding_id"], str)
        and len(rollback["rollback_binding_id"]) >= 8,
        "bad rollback binding ID",
    )
    require(rollback["rollback_defined"] is True, "rollback is not defined")
    require(
        rollback["rollback_binding_verified"] is True,
        "rollback binding is not verified",
    )
    require(
        SHA_PATTERN.fullmatch(rollback["rollback_document_sha256"]) is not None,
        "bad rollback document SHA-256",
    )

    files = manifest["files"]
    require(isinstance(files, list), "files must be an array")
    require(len(files) == 8, "manifest must contain exactly eight files")

    observed_sources: set[str] = set()
    observed_destinations: set[str] = set()

    file_fields = {
        "source",
        "destination",
        "sha256",
        "mode",
        "owner",
        "group",
        "destination_preexisting",
    }

    for index, item in enumerate(files):
        item = exact_keys(item, file_fields, f"files[{index}]")
        source = item["source"]
        require(source in FILE_MAP, f"unexpected source: {source}")
        destination, mode = FILE_MAP[source]

        require(
            item["destination"] == destination,
            f"destination mismatch for {source}",
        )
        require(item["mode"] == mode, f"mode mismatch for {source}")
        require(item["owner"] == "root", f"owner mismatch for {source}")
        require(item["group"] == "root", f"group mismatch for {source}")
        require(
            isinstance(item["destination_preexisting"], bool),
            f"bad destination_preexisting for {source}",
        )
        require(
            SHA_PATTERN.fullmatch(item["sha256"]) is not None,
            f"bad source SHA-256 for {source}",
        )
        require(source not in observed_sources, f"duplicate source: {source}")
        require(
            destination not in observed_destinations,
            f"duplicate destination: {destination}",
        )

        source_path = repository / source
        require(source_path.is_file(), f"source missing: {source}")
        require(
            sha256_file(source_path) == item["sha256"],
            f"source hash mismatch: {source}",
        )

        observed_sources.add(source)
        observed_destinations.add(destination)

    require(observed_sources == set(FILE_MAP), "source set is incomplete")

    runtime = exact_keys(
        manifest["runtime"],
        {
            "request_file",
            "request_file_mode",
            "evidence_directory",
            "evidence_directory_mode",
            "runtime_owner",
        },
        "runtime",
    )
    require(
        runtime
        == {
            "request_file":
                "/var/lib/spot/controlled-read-observe/request.json",
            "request_file_mode": "0600",
            "evidence_directory":
                "/var/lib/spot/controlled-read-observe/evidence",
            "evidence_directory_mode": "0700",
            "runtime_owner": "root",
        },
        "runtime boundary mismatch",
    )

    planned = exact_keys(
        manifest["planned_service_state"],
        {
            "daemon_reload_planned",
            "service_activation_planned",
            "timer_installation_planned",
            "observer_enabled",
            "observer_scheduled",
        },
        "planned_service_state",
    )
    require(planned["daemon_reload_planned"] is True, "reload not declared")
    for field in (
        "service_activation_planned",
        "timer_installation_planned",
        "observer_enabled",
        "observer_scheduled",
    ):
        require(planned[field] is False, f"unsafe planned state: {field}")

    governance = exact_keys(
        manifest["governance"],
        {
            "spot_core_sole_authority",
            "worker_self_apply_allowed",
            "activation_authorized",
            "scheduling_authorized",
            "production_observation_authorized",
            "live_executor_enabled",
            "execution_allowed",
            "mutation_authority",
        },
        "governance",
    )
    require(
        governance["spot_core_sole_authority"] is True,
        "Spot Core sole authority missing",
    )
    for field in (
        "worker_self_apply_allowed",
        "activation_authorized",
        "scheduling_authorized",
        "production_observation_authorized",
        "live_executor_enabled",
        "execution_allowed",
        "mutation_authority",
    ):
        require(governance[field] is False, f"unsafe governance state: {field}")

    if verify_references:
        references = (
            (
                repository / authorization["record_path"],
                authorization["record_sha256"],
                "authorization",
            ),
            (
                repository / review["review_pass_path"],
                review["review_pass_sha256"],
                "review",
            ),
            (
                Path(backup["backup_manifest_path"]),
                backup["backup_manifest_sha256"],
                "backup manifest",
            ),
            (
                repository / rollback["rollback_document"],
                rollback["rollback_document_sha256"],
                "rollback document",
            ),
        )

        for path, expected_sha, label in references:
            require(path.is_file(), f"{label} missing: {path}")
            require(
                sha256_file(path) == expected_sha,
                f"{label} hash mismatch",
            )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate a K21C installation manifest."
    )
    parser.add_argument("manifest", type=Path)
    parser.add_argument(
        "--repository",
        type=Path,
        default=Path.cwd(),
    )
    args = parser.parse_args()

    try:
        payload = json.loads(args.manifest.read_text(encoding="utf-8"))
        require(isinstance(payload, dict), "manifest must be an object")
        validate_manifest(payload, args.repository.resolve())
    except (OSError, json.JSONDecodeError, ManifestError) as exc:
        print(f"[DENY] invalid K21C installation manifest: {exc}", file=sys.stderr)
        return 2

    print("[PASS] K21C installation manifest valid")
    print("system_path_installation_authorized=true")
    print("activation_authorized=false")
    print("scheduling_authorized=false")
    print("production_observation_authorized=false")
    print("execution_allowed=false")
    print("mutation_authority=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

## Source: watch/observe/controlled-read-observe-install-manifest-failure-test.py

```python
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
            "system_path_installation_authorized": True,
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
            "daemon_reload_planned": True,
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
            "system-path authorization false",
            lambda value: value["authorization"].update(
                {"system_path_installation_authorized": False}
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
```

