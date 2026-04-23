from __future__ import annotations

import json
import os
import sys

from spot_mcp_client import SpotClient


def print_json(label: str, payload: object) -> None:
    print(f"\n=== {label} ===")
    print(json.dumps(payload, indent=2, sort_keys=True))


def main() -> int:
    base_url = os.environ.get("SPOT_BASE_URL", "http://127.0.0.1:8787")
    admin_token = os.environ.get("SPOT_ADMIN_TOKEN", "").strip()

    if not admin_token:
        print("ERROR: SPOT_ADMIN_TOKEN is not set")
        return 1

    client = SpotClient(base_url=base_url, admin_token=admin_token)

    try:
        print_json("health", client.health())
        print_json("routing", client.routing())
        print_json("fleet_ping", client.fleet_ping())
        print_json("stats_latency", client.stats_latency())
        print_json("recent_decisions", client.recent_decisions(limit=5))
        print_json(
            "routing_audit",
            client.routing_audit(limit=20),
        )
        print_json(
            "validate",
            client.validate(
                worker="spot-worker-01",
                commands=[
                    "systemctl is-active ollama",
                    "ls /home/ogre",
                ],
            ),
        )
    except Exception as exc:
        print(f"ERROR: {exc!r}")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
