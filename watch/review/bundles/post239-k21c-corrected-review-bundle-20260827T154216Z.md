# Post-2.39 K21C Corrected Implementation Review

## Review scope

Review the corrected disposition of Worker-05's two blocking findings.
This bundle is bound to the earlier complete source review.

- previous full bundle: `watch/review/bundles/post239-k21c-installation-contract-review-bundle-20260826T145142Z.md`
- previous full bundle SHA-256: `8ba19f20dbdf663af4283866e305f752ed5fe2cc65bae0cf51476b3adc851df3`
- repository head: `11850954445808e74e6c46007ce4c7961fcb04f2`
- generated UTC: `2026-08-27T15:42:17Z`

## Previous blocking findings

1. Manifest schema allowed unauthorized system-path installation.
2. Manifest planned an unauthorized daemon-reload.

## Required corrected state

- system-path installation authorized: false
- daemon-reload planned: false
- daemon-reload authorized: false
- daemon-reload performed: false
- installation performed: false
- activation authorized: false
- scheduling authorized: false
- production observation authorized: false
- execution_allowed: false
- mutation_authority: false

## Corrected source identities

- `watch/observe/controlled-read-observe-install-manifest-schema-v1.json`: `4b817ee7485b99382e634ef085580bca99c433f7a60ad0ef80fc414193ba94a0`
- `watch/observe/controlled-read-observe-install-manifest-validate.py`: `6bd9301d2246b38a77532da0bec49fcbb8478e194b57d77443f90d4b3e9999fd`
- `watch/observe/controlled-read-observe-install-manifest-failure-test.py`: `14aa4171560bf49a7cc4c1ba8119531657784f769cd2042de2438d7a9e960503`
- `watch/observe/controlled-read-observe-install-validate.py`: `d0d17664cdecf2cff194c2410315b24f1fdd15e946ad0e846d4f4eadc62a4616`

## Corrected schema locks

```json
{
  "system_path_installation_authorized": false,
  "daemon_reload_planned": false
}
```

## Corrected manifest-validator controls

```python
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
        authorization["system_path_installation_authorized"] is False,
        "system-path installation authority expanded",
    )
    require(
        SHA_PATTERN.fullmatch(authorization["record_sha256"]) is not None,
        "bad authorization record SHA-256",
    )

    review = exact_keys(
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
    require(
        planned["daemon_reload_planned"] is False,
        "daemon-reload planning authority expanded",
    )
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
    try:
        payload = json.loads(args.manifest.read_text(encoding="utf-8"))
        require(isinstance(payload, dict), "manifest must be an object")
        validate_manifest(payload, args.repository.resolve())
    except (OSError, json.JSONDecodeError, ManifestError) as exc:
        print(f"[DENY] invalid K21C installation manifest: {exc}", file=sys.stderr)
        return 2

    print("[PASS] K21C installation manifest valid")
    print("system_path_installation_authorized=false")
    print("activation_authorized=false")
    print("scheduling_authorized=false")
    print("production_observation_authorized=false")
    print("execution_allowed=false")
    print("mutation_authority=false")
    return 0
```

## Corrected adversarial cases

```python
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
```

## Higher-level contract enforcement

```python
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

```

## Regression results

```text
/tmp/tmp.wvgZa3stLw:[PASS] complete K21A offline suite
/tmp/tmp.uFvBw8v1Nn:pass=4 fail=0
/tmp/tmp.uFvBw8v1Nn:RESULT: POST-2.39 K21B VALIDATION PASS
/tmp/tmp.APo9KqtJNe:pass=7 fail=0
/tmp/tmp.APo9KqtJNe:RESULT: POST-2.39 K21C INSTALL CONTRACT VALIDATION PASS
/tmp/tmp.0A1AB4iYUE:positive_tests=1
/tmp/tmp.0A1AB4iYUE:negative_tests=26
/tmp/tmp.0A1AB4iYUE:RESULT: POST-2.39 K21C MANIFEST FAILURE TEST PASS
```

## Review instruction

Return PASS only if both previous blockers are fixed, the new adversarial
tests reject both authority expansions, and every runtime authority remains
false. This review grants no installation or runtime authority.
