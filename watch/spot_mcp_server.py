from __future__ import annotations

import json
import os
from typing import Any

from mcp.server.fastmcp import FastMCP

from spot_mcp_client import SpotClient


APP_NAME = "spot-mcp"
mcp = FastMCP(APP_NAME)


def _client() -> SpotClient:
    return SpotClient(
        base_url=os.environ.get("SPOT_BASE_URL", "http://127.0.0.1:8787").rstrip("/"),
        admin_token=os.environ.get("SPOT_ADMIN_TOKEN", "").strip(),
    )


def _json(payload: Any) -> str:
    return json.dumps(payload, indent=2, sort_keys=True)


@mcp.tool()
def spot_health() -> str:
    """Return Spot control-plane health."""
    return _json(_client().health())


@mcp.tool()
def spot_routing() -> str:
    """Return current routing state and active request metadata."""
    return _json(_client().routing())


@mcp.tool()
def spot_fleet_ping() -> str:
    """Return fleet health snapshot for all workers."""
    return _json(_client().fleet_ping())


@mcp.tool()
def spot_routing_audit(limit: int = 50) -> str:
    """Return routing audit summary and recent items."""
    return _json(_client().routing_audit(limit=limit))


@mcp.tool()
def spot_validate(worker: str, commands: list[str]) -> str:
    """Run allowlisted validation commands on a worker."""
    return _json(_client().validate(worker=worker, commands=commands))


@mcp.tool()
def spot_read_file(worker: str, path: str) -> str:
    """Read a file from a worker node."""
    return _json(_client().read_file(worker=worker, path=path))


@mcp.tool()
def spot_write_file(worker: str, path: str, content: str) -> str:
    """Write a file to a worker node."""
    return _json(_client().write_file(worker=worker, path=path, content=content))


@mcp.tool()
def spot_restart_service(worker: str, service: str) -> str:
    """Restart an allowlisted service on a worker node."""
    return _json(_client().restart_service(worker=worker, service=service))


@mcp.tool()
def spot_read_local_file(path: str) -> str:
    """Read a local file from spot-core via the Spot admin API."""
    return _json(_client().read_local_file(path=path))


@mcp.tool()
def spot_write_local_file(path: str, content: str) -> str:
    """Write a local file on spot-core via the Spot admin API."""
    return _json(_client().write_local_file(path=path, content=content))


if __name__ == "__main__":
    mcp.run(transport="sse")
