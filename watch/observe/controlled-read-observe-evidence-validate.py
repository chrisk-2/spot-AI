#!/usr/bin/env python3
"""Validate controlled read/observe evidence without performing an observation."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from controlled_read_observe_validation_v1 import ContractError, validate_evidence


def load_instance(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ContractError(f"cannot load evidence JSON {path}: {exc}") from exc

    if not isinstance(payload, dict):
        raise ContractError("evidence top-level JSON must be an object")

    return payload


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Offline validation for controlled read/observe evidence."
    )
    parser.add_argument("evidence", type=Path)
    args = parser.parse_args()

    try:
        payload = load_instance(args.evidence)
        validate_evidence(payload)
    except ContractError as exc:
        print(f"[DENY] controlled read/observe evidence rejected: {exc}", file=sys.stderr)
        return 1

    print("[PASS] controlled read/observe evidence accepted offline")
    print(f"observation_id={payload['observation_id']}")
    print(f"request_id={payload['request_id']}")
    print(f"policy_decision={payload['policy_decision']}")
    print("execution_attempted=false")
    print("observation_attempted=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
