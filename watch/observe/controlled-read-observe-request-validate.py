#!/usr/bin/env python3
"""Validate a controlled read/observe request without performing it."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from controlled_read_observe_validation_v1 import ContractError, validate_request


def load_instance(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ContractError(f"cannot load request JSON {path}: {exc}") from exc

    if not isinstance(payload, dict):
        raise ContractError("request top-level JSON must be an object")

    return payload


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Offline validation for a controlled read/observe request."
    )
    parser.add_argument("request", type=Path)
    args = parser.parse_args()

    try:
        payload = load_instance(args.request)
        validate_request(payload)
    except ContractError as exc:
        print(f"[DENY] controlled read/observe request rejected: {exc}", file=sys.stderr)
        return 1

    print("[PASS] controlled read/observe request accepted offline")
    print(f"observation_id={payload['observation_id']}")
    print(f"request_id={payload['request_id']}")
    print("execution_attempted=false")
    print("observation_attempted=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
