#!/usr/bin/env python3
from __future__ import annotations

import asyncio
import json
from typing import Any

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

MCP_URL = "http://127.0.0.1:8000/mcp"

REQUIRED_TOOLS = {
    "admin_host_liveness",
    "admin_visibility_probe",
    "admin_opnsense_dhcp_probe",
    "unifi_devices",
    "unifi_networks",
    "opn_dhcp_leases",
}


def extract_json_objects(result: Any) -> list[Any]:
    objects = []
    for item in getattr(result, "content", []) or []:
        text = getattr(item, "text", None)
        if not text:
            continue
        try:
            objects.append(json.loads(text))
        except Exception:
            objects.append(text)
    return objects


async def call(session: ClientSession, name: str, args: dict | None = None) -> list[Any]:
    result = await session.call_tool(name, args or {})
    objects = extract_json_objects(result)

    print(f"\n===== {name} summary =====")

    if name == "admin_host_liveness":
        summary = [
            {
                "name": item.get("name"),
                "ip": item.get("ip"),
                "reachable": item.get("reachable"),
                "method": item.get("method"),
                "port_checks": item.get("port_checks", []),
            }
            for item in objects
            if isinstance(item, dict)
        ]
        print(json.dumps(summary, indent=2))
        return objects

    payload = objects[0] if objects else {}

    if name in {"unifi_devices", "unifi_networks"}:
        if isinstance(payload, dict):
            print(json.dumps({
                "rc": payload.get("meta", {}).get("rc"),
                "count": len(payload.get("data", [])) if isinstance(payload.get("data"), list) else None,
            }, indent=2))
        else:
            print(str(payload)[:1000])
        return objects

    if name in {"opn_dhcp_leases", "admin_opnsense_dhcp_probe"}:
        if name == "admin_opnsense_dhcp_probe" and isinstance(payload, dict) and "result" in payload:
            payload = payload["result"]

        if isinstance(payload, dict):
            meta = payload.get("meta", {})
            data = payload.get("data", [])
            print(json.dumps({
                "errorMessage": payload.get("errorMessage"),
                "checked": payload.get("checked"),
                "meta": meta,
                "count": len(data) if isinstance(data, list) else None,
                "attempts_tail": payload.get("attempts", [])[-10:],
            }, indent=2))
        else:
            print(str(payload)[:1000])
        return objects

    print(json.dumps(objects, indent=2, default=str))
    return objects


async def main() -> int:
    async with streamablehttp_client(MCP_URL) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()

            tools = await session.list_tools()
            names = sorted(tool.name for tool in tools.tools)

            print("===== LIVE MCP TOOL REGISTRY CHECK =====")
            missing = sorted(REQUIRED_TOOLS - set(names))
            print(json.dumps({"missing": missing, "required_present": not missing}, indent=2))
            if missing:
                return 10

            await call(session, "admin_visibility_probe")

            liveness = await call(session, "admin_host_liveness", {"targets": "all"})
            live_names = {
                item.get("name")
                for item in liveness
                if isinstance(item, dict) and item.get("reachable") is True
            }
            expected_hosts = {"dns-core", "starfleet-tower", "unimatrix6", "spot-ui-01"}
            if not expected_hosts.issubset(live_names):
                print(f"FAIL: missing live host proofs: {sorted(expected_hosts - live_names)}")
                return 20

            devices = await call(session, "unifi_devices")
            devices_payload = devices[0] if devices else {}
            if not isinstance(devices_payload, dict) or devices_payload.get("meta", {}).get("rc") != "ok":
                print("FAIL: unifi_devices did not return rc=ok")
                return 30

            networks = await call(session, "unifi_networks")
            networks_payload = networks[0] if networks else {}
            if not isinstance(networks_payload, dict) or networks_payload.get("meta", {}).get("rc") != "ok":
                print("FAIL: unifi_networks did not return rc=ok")
                return 31

            dhcp = await call(session, "opn_dhcp_leases")
            dhcp_payload = dhcp[0] if dhcp else {}
            if not isinstance(dhcp_payload, dict):
                print("FAIL: opn_dhcp_leases returned non-dict payload")
                return 40
            if dhcp_payload.get("errorMessage"):
                print("FAIL: opn_dhcp_leases returned errorMessage")
                return 41
            if dhcp_payload.get("meta", {}).get("rc") != "ok":
                print("FAIL: opn_dhcp_leases did not return meta.rc=ok")
                return 42

            print("\nPASS: live MCP visibility verification complete")
            return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
