#!/usr/bin/env python3
"""Offline replay, identity-collision, timeout, and output-bound tests."""

from __future__ import annotations

import copy
from typing import Any, Callable

from controlled_read_observe_validation_v1 import (
    ContractError,
    canonical_sha256,
    validate_evidence,
    validate_request,
)


def valid_request() -> dict[str, Any]:
    return {
        "schema": "spot_controlled_read_observe_request_v1",
        "observation_id": "OBS-K21A-BASE0001",
        "request_id": "K21A-REQUEST-BASE0001",
        "requested_at": "2026-08-06T18:30:00Z",
        "hostname": "spot-core",
        "observer_identity": "spot-offline-k21a-test",
        "observation_class": "http",
        "target": "http://127.0.0.1:8787/health",
        "operation": "http_get",
        "timeout_seconds": 10,
        "output_bytes_max": 65536,
        "execution_allowed": False,
        "mutation_authority": False,
        "live_executor_enabled": False,
    }


def valid_evidence(request: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema": "spot_controlled_read_observe_evidence_v1",
        "observation_id": request["observation_id"],
        "request_id": request["request_id"],
        "timestamp": "2026-08-06T18:30:02Z",
        "hostname": "spot-core",
        "observer_identity": request["observer_identity"],
        "observation_class": request["observation_class"],
        "target": request["target"],
        "operation": request["operation"],
        "started_at": "2026-08-06T18:30:00Z",
        "completed_at": "2026-08-06T18:30:01Z",
        "timeout_seconds": request["timeout_seconds"],
        "exit_status": 0,
        "http_status": 200,
        "output_bytes": 22,
        "output_truncated": False,
        "output_sha256": "0" * 64,
        "classification": "healthy",
        "policy_decision": "allowed_read_only",
        "execution_allowed": False,
        "mutation_authority": False,
        "live_executor_enabled": False,
        "remediation_performed": False,
        "service_action_performed": False,
        "network_stack_mutation": False,
    }


class OfflineIdentityLedger:
    """In-memory test oracle. It performs no I/O and authorizes no action."""

    def __init__(self) -> None:
        self.observations: dict[str, str] = {}
        self.request_identities: dict[str, str] = {}

    def register(self, payload: dict[str, Any]) -> str:
        validate_request(payload)
        digest = canonical_sha256(payload)
        observation_id = payload["observation_id"]
        request_id = payload["request_id"]

        observation_digest = self.observations.get(observation_id)
        request_digest = self.request_identities.get(request_id)

        if observation_digest is not None and observation_digest != digest:
            raise ContractError("observation_id collision")
        if request_digest is not None and request_digest != digest:
            raise ContractError("request_id collision")

        self.observations[observation_id] = digest
        self.request_identities[request_id] = digest
        return "replay_identical" if observation_digest == digest else "registered"


def expect_rejected(
    name: str,
    validator: Callable[[dict[str, Any]], None],
    payload: dict[str, Any],
) -> None:
    try:
        validator(payload)
    except ContractError:
        print(f"[PASS] rejected: {name}")
    else:
        raise AssertionError(f"negative contract accepted: {name}")


def main() -> int:
    request = valid_request()
    evidence = valid_evidence(request)

    validate_request(request)
    validate_evidence(evidence)
    print("[PASS] baseline request and evidence accepted")

    digest_a = canonical_sha256(request)
    digest_b = canonical_sha256(copy.deepcopy(request))
    assert digest_a == digest_b
    print("[PASS] canonical request digest is deterministic")

    reordered = dict(reversed(list(request.items())))
    assert canonical_sha256(reordered) == digest_a
    print("[PASS] canonical digest is key-order independent")

    changed = copy.deepcopy(request)
    changed["timeout_seconds"] = 9
    assert canonical_sha256(changed) != digest_a
    print("[PASS] material request change alters digest")

    ledger = OfflineIdentityLedger()
    assert ledger.register(request) == "registered"
    assert ledger.register(copy.deepcopy(request)) == "replay_identical"
    print("[PASS] byte-equivalent identity replay is deterministic")

    collision = copy.deepcopy(request)
    collision["timeout_seconds"] = 9
    expect_rejected(
        "same observation_id with changed payload",
        ledger.register,
        collision,
    )

    collision = copy.deepcopy(request)
    collision["observation_id"] = "OBS-K21A-OTHER001"
    collision["output_bytes_max"] = 4096
    expect_rejected(
        "same request_id with changed payload",
        ledger.register,
        collision,
    )

    timeout_min = copy.deepcopy(request)
    timeout_min["observation_id"] = "OBS-K21A-TIMEOUT01"
    timeout_min["request_id"] = "K21A-REQUEST-TIMEOUT01"
    timeout_min["timeout_seconds"] = 1
    validate_request(timeout_min)
    print("[PASS] request minimum timeout accepted")

    timeout_max = copy.deepcopy(request)
    timeout_max["observation_id"] = "OBS-K21A-TIMEOUT15"
    timeout_max["request_id"] = "K21A-REQUEST-TIMEOUT15"
    timeout_max["timeout_seconds"] = 15
    validate_request(timeout_max)
    print("[PASS] request maximum timeout accepted")

    output_min = copy.deepcopy(request)
    output_min["observation_id"] = "OBS-K21A-OUTPUT001"
    output_min["request_id"] = "K21A-REQUEST-OUTPUT001"
    output_min["output_bytes_max"] = 1
    validate_request(output_min)
    print("[PASS] request minimum output bound accepted")

    output_max = copy.deepcopy(request)
    output_max["observation_id"] = "OBS-K21A-OUTPUTMAX"
    output_max["request_id"] = "K21A-REQUEST-OUTPUTMAX"
    output_max["output_bytes_max"] = 65536
    validate_request(output_max)
    print("[PASS] request maximum output bound accepted")

    evidence_zero = copy.deepcopy(evidence)
    evidence_zero["output_bytes"] = 0
    evidence_zero["output_sha256"] = (
        "e3b0c44298fc1c149afbf4c8996fb924"
        "27ae41e4649b934ca495991b7852b855"
    )
    validate_evidence(evidence_zero)
    print("[PASS] zero-byte evidence accepted")

    evidence_max = copy.deepcopy(evidence)
    evidence_max["output_bytes"] = 65536
    evidence_max["output_truncated"] = True
    validate_evidence(evidence_max)
    print("[PASS] maximum bounded evidence accepted")

    journal = copy.deepcopy(request)
    journal.update(
        {
            "observation_id": "OBS-K21A-JOURNAL1",
            "request_id": "K21A-REQUEST-JOURNAL1",
            "observation_class": "journal",
            "target": "spot-mcp.service",
            "operation": "journal_read",
            "journal_lines": 200,
            "journal_lookback_seconds": 3600,
        }
    )
    validate_request(journal)
    print("[PASS] maximum journal bounds accepted")

    negative_cases: list[
        tuple[str, Callable[[dict[str, Any]], None], dict[str, Any]]
    ] = []

    payload = copy.deepcopy(request)
    payload["timeout_seconds"] = 0
    negative_cases.append(("timeout below minimum", validate_request, payload))

    payload = copy.deepcopy(request)
    payload["timeout_seconds"] = 16
    negative_cases.append(("timeout above maximum", validate_request, payload))

    payload = copy.deepcopy(request)
    payload["output_bytes_max"] = 0
    negative_cases.append(("output bound below minimum", validate_request, payload))

    payload = copy.deepcopy(request)
    payload["output_bytes_max"] = 65537
    negative_cases.append(("output bound above maximum", validate_request, payload))

    payload = copy.deepcopy(evidence)
    payload["timeout_seconds"] = 0
    negative_cases.append(
        ("evidence timeout below minimum", validate_evidence, payload)
    )

    payload = copy.deepcopy(evidence)
    payload["timeout_seconds"] = 16
    negative_cases.append(
        ("evidence timeout above maximum", validate_evidence, payload)
    )

    payload = copy.deepcopy(evidence)
    payload["output_bytes"] = -1
    negative_cases.append(
        ("evidence output below minimum", validate_evidence, payload)
    )

    payload = copy.deepcopy(evidence)
    payload["output_bytes"] = 65537
    negative_cases.append(
        ("evidence output above maximum", validate_evidence, payload)
    )

    payload = copy.deepcopy(journal)
    payload["journal_lines"] = 0
    negative_cases.append(
        ("journal lines below minimum", validate_request, payload)
    )

    payload = copy.deepcopy(journal)
    payload["journal_lines"] = 201
    negative_cases.append(
        ("journal lines above maximum", validate_request, payload)
    )

    payload = copy.deepcopy(journal)
    payload["journal_lookback_seconds"] = 0
    negative_cases.append(
        ("journal lookback below minimum", validate_request, payload)
    )

    payload = copy.deepcopy(journal)
    payload["journal_lookback_seconds"] = 3601
    negative_cases.append(
        ("journal lookback above maximum", validate_request, payload)
    )

    for name, validator, payload in negative_cases:
        expect_rejected(name, validator, payload)

    print("deterministic_digest_tests=3")
    print("replay_tests=2")
    print("collision_tests=2")
    print("positive_bound_tests=7")
    print(f"negative_bound_tests={len(negative_cases)}")
    print("observer_implemented=false")
    print("observation_attempted=false")
    print("execution_attempted=false")
    print("execution_allowed=false")
    print("mutation_authority=false")
    print("live_executor_enabled=false")
    print("[PASS] complete K21A offline suite")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
