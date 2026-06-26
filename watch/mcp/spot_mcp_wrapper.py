#!/usr/bin/env python3
from __future__ import annotations
import os
from typing import Any
import httpx
import uvicorn
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings

APP_NAME = "Spot MCP"
SPOT_API_BASE = os.environ.get("SPOT_API_BASE", "http://127.0.0.1:8787").rstrip("/")
SPOT_ADMIN_TOKEN = os.environ.get("SPOT_ADMIN_TOKEN", "").strip()

mcp = FastMCP(
    APP_NAME,
    json_response=True,
    stateless_http=True,
    transport_security=TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=[
            "127.0.0.1:*",
            "localhost:*",
            "mcp.starfleetcore.com",
            "mcp.starfleetcore.com:443",
        ],
        allowed_origins=[
            "https://mcp.starfleetcore.com",
            "http://127.0.0.1:*",
            "http://localhost:*",
        ],
    ),
)

async def _request(method: str, path: str, *, json_body=None):
    url = f"{SPOT_API_BASE}{path}"
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.request(method, url, json=json_body)
    try:
        data = resp.json()
    except Exception:
        data = {"status": resp.status_code, "text": resp.text}
    if resp.status_code >= 400:
        raise Exception(f"{method} {path} failed: {data}")
    return data

async def _admin_post(path: str, payload: dict[str, Any]):
    return await _request("POST", path, json_body={"token": SPOT_ADMIN_TOKEN, **payload})

@mcp.tool()
async def health():
    return await _request("GET", "/health")

@mcp.tool()
async def routing():
    return await _request("GET", "/routing")

@mcp.tool()
async def fleet_ping():
    return await _request("GET", "/fleet/ping")

@mcp.tool()
async def stats_latency():
    return await _request("GET", "/stats/latency")

@mcp.tool()
async def stats_recent_decisions():
    return await _request("GET", "/stats/recent-decisions")

@mcp.tool()
async def stats_routing_audit():
    return await _request("GET", "/stats/routing-audit")

@mcp.tool()
async def admin_read_file(worker: str, path: str):
    return await _admin_post("/admin/read-file", {"worker": worker, "path": path})

@mcp.tool()
async def admin_write_file(worker: str, path: str, content: str):
    return await _admin_post("/admin/write-file", {"worker": worker, "path": path, "content": content})

@mcp.tool()
async def admin_read_local_file(path: str):
    return await _admin_post("/admin/read-local-file", {"path": path})

@mcp.tool()
async def admin_write_local_file(path: str, content: str):
    return await _admin_post("/admin/write-local-file", {"path": path, "content": content})

@mcp.tool()
async def admin_write_ui_file(filename: str, content: str):
    """Write a file to the Starfleet UI source directory and trigger a rebuild.
    Use filename only (e.g. 'App.jsx'), not a full path."""
    return await _admin_post("/admin/write-ui-file", {"filename": filename, "content": content})

@mcp.tool()
async def admin_validate(worker: str, commands: list[str]):
    return await _admin_post("/admin/validate", {"worker": worker, "commands": commands})

@mcp.tool()
async def admin_restart_service(worker: str, service: str):
    return await _admin_post("/admin/restart-service", {"worker": worker, "service": service})

@mcp.tool()
async def admin_quarantine(worker: str, seconds: int = 1800):
    return await _admin_post("/admin/quarantine", {"worker": worker, "seconds": seconds})

@mcp.tool()
async def admin_release(worker: str):
    return await _admin_post("/admin/release", {"worker": worker})

@mcp.tool()
async def admin_operator_command(command: str):
    return await _admin_post("/admin/operator-command", {"command": command})


# ─── Network clients ──────────────────────────────────────────────────────────

OPNSENSE_HOST   = os.environ.get("OPNSENSE_HOST", "192.168.1.1")
OPNSENSE_KEY    = os.environ.get("OPNSENSE_KEY", "")
OPNSENSE_SECRET = os.environ.get("OPNSENSE_SECRET", "")

UNIFI_HOST = os.environ.get("UNIFI_HOST", "192.168.60.20")
UNIFI_PORT = os.environ.get("UNIFI_PORT", "11443")
UNIFI_USER = os.environ.get("UNIFI_USER", "")
UNIFI_PASS = os.environ.get("UNIFI_PASS", "")
UNIFI_SITE = os.environ.get("UNIFI_SITE", "starfleet")

async def _opn(method: str, path: str, *, json_body=None):
    """Call OPNsense API with key/secret auth."""
    url = f"https://{OPNSENSE_HOST}/api{path}"
    async with httpx.AsyncClient(verify=False, timeout=30) as client:
        resp = await client.request(
            method, url,
            auth=(OPNSENSE_KEY, OPNSENSE_SECRET),
            json=json_body,
        )
    try:
        return resp.json()
    except Exception:
        return {"status": resp.status_code, "text": resp.text}

async def _unifi(method: str, path: str, *, json_body=None):
    """Call UniFi OS API — handles login/cookie/CSRF automatically."""
    base = f"https://{UNIFI_HOST}:{UNIFI_PORT}"
    async with httpx.AsyncClient(verify=False, timeout=30) as client:
        login = await client.post(
            f"{base}/api/auth/login",
            json={"username": UNIFI_USER, "password": UNIFI_PASS},
        )
        csrf = login.headers.get("x-csrf-token", "")
        headers = {"x-csrf-token": csrf} if csrf else {}
        resp = await client.request(
            method,
            f"{base}/proxy/network/api/s/{UNIFI_SITE}{path}",
            json=json_body,
            headers=headers,
        )
    try:
        return resp.json()
    except Exception:
        return {"status": resp.status_code, "text": resp.text}

# ─── OPNsense tools ───────────────────────────────────────────────────────────

@mcp.tool()
async def opn_firewall_rules():
    """List all OPNsense firewall filter rules."""
    return await _opn("GET", "/firewall/filter/searchRule")

@mcp.tool()
async def opn_create_firewall_rule(
    description: str,
    action: str,
    interface: str,
    protocol: str,
    source_net: str,
    destination_net: str,
    destination_port: str = "any",
    direction: str = "in",
):
    """Create an OPNsense firewall rule.
    action: pass|block|reject
    direction: in|out
    protocol: any|TCP|UDP|ICMP etc.
    source_net/destination_net: CIDR or 'any'
    """
    payload = {
        "rule": {
            "enabled": "1",
            "action": action,
            "interface": interface,
            "direction": direction,
            "ipprotocol": "inet",
            "protocol": protocol,
            "source_net": source_net,
            "destination_net": destination_net,
            "destination_port": destination_port,
            "description": description,
        }
    }
    result = await _opn("POST", "/firewall/filter/addRule", json_body=payload)
    await _opn("POST", "/firewall/filter/apply")
    return result

@mcp.tool()
async def opn_delete_firewall_rule(rule_uuid: str):
    """Delete an OPNsense firewall rule by UUID and apply."""
    result = await _opn("POST", f"/firewall/filter/delRule/{rule_uuid}")
    await _opn("POST", "/firewall/filter/apply")
    return result

@mcp.tool()
async def opn_aliases():
    """List all OPNsense firewall aliases."""
    return await _opn("GET", "/firewall/alias/searchItem")

@mcp.tool()
async def opn_create_alias(name: str, alias_type: str, content: list, description: str = ""):
    """Create an OPNsense alias.
    alias_type: host|network|port
    content: list of IPs, CIDRs, or ports
    """
    payload = {
        "alias": {
            "enabled": "1",
            "name": name,
            "type": alias_type,
            "content": "\n".join(content),
            "description": description,
        }
    }
    result = await _opn("POST", "/firewall/alias/addItem", json_body=payload)
    await _opn("POST", "/firewall/alias/reconfigure")
    return result

@mcp.tool()
async def opn_vlans():
    """List all OPNsense VLANs."""
    return await _opn("GET", "/interfaces/vlan/searchItem")

@mcp.tool()
async def opn_create_vlan(parent_interface: str, vlan_tag: int, description: str = ""):
    """Create an OPNsense VLAN.
    parent_interface: e.g. 'igc0', 'em0'
    vlan_tag: 1-4094
    """
    payload = {
        "vlan": {
            "if": parent_interface,
            "tag": str(vlan_tag),
            "pcp": "0",
            "descr": description,
        }
    }
    result = await _opn("POST", "/interfaces/vlan/addItem", json_body=payload)
    await _opn("POST", "/interfaces/vlan/reconfigure")
    return result

@mcp.tool()
async def opn_dhcp_leases():
    """List all OPNsense DHCP leases."""
    return await _opn("GET", "/dhcpv4/leases/searchLease")

@mcp.tool()
async def opn_create_static_lease(interface: str, mac: str, ip: str, hostname: str = ""):
    """Create an OPNsense DHCP static lease."""
    payload = {
        "lease": {
            "interface": interface,
            "mac": mac,
            "ipaddr": ip,
            "hostname": hostname,
        }
    }
    return await _opn("POST", "/dhcpv4/settings/addStaticMap", json_body=payload)

@mcp.tool()
async def opn_dns_overrides():
    """List all Unbound DNS host overrides."""
    return await _opn("GET", "/unbound/settings/searchHostOverride")

@mcp.tool()
async def opn_create_dns_override(hostname: str, domain: str, ip: str, description: str = ""):
    """Create an Unbound DNS host override."""
    payload = {
        "host": {
            "enabled": "1",
            "hostname": hostname,
            "domain": domain,
            "rr": "A",
            "server": ip,
            "description": description,
        }
    }
    result = await _opn("POST", "/unbound/settings/addHostOverride", json_body=payload)
    await _opn("POST", "/unbound/service/reconfigure")
    return result

@mcp.tool()
async def opn_interfaces():
    """List OPNsense interface status."""
    return await _opn("GET", "/interfaces/overview/interfacesInfo")

@mcp.tool()
async def opn_gateways():
    """List OPNsense gateway status."""
    return await _opn("GET", "/routes/gateway/status")

@mcp.tool()
async def opn_wol(interface: str, mac: str):
    """Send Wake-on-LAN packet via OPNsense."""
    return await _opn("POST", "/wol/wol/set", json_body={"wake": {"interface": interface, "mac": mac}})

@mcp.tool()
async def opn_wireguard_status():
    """Get WireGuard peer status from OPNsense."""
    return await _opn("GET", "/wireguard/service/show")

@mcp.tool()
async def opn_restart_wireguard():
    """Restart WireGuard on OPNsense."""
    return await _opn("POST", "/wireguard/service/restart")

# ─── UniFi tools ──────────────────────────────────────────────────────────────

@mcp.tool()
async def unifi_devices():
    """List all UniFi devices (switches, APs, gateways)."""
    return await _unifi("GET", "/stat/device")

@mcp.tool()
async def unifi_clients():
    """List all active UniFi clients."""
    return await _unifi("GET", "/stat/sta")

@mcp.tool()
async def unifi_networks():
    """List all UniFi networks/VLANs."""
    return await _unifi("GET", "/rest/networkconf")

@mcp.tool()
async def unifi_create_network(name: str, vlan_id: int, purpose: str = "corporate", subnet: str = ""):
    """Create a UniFi network with optional VLAN tag.
    purpose: corporate|guest|vlan-only
    subnet: e.g. '192.168.100.0/24' (optional for vlan-only)
    """
    payload = {
        "name": name,
        "purpose": purpose,
        "vlan_enabled": True,
        "vlan": vlan_id,
    }
    if subnet:
        payload["ip_subnet"] = subnet
        payload["dhcpd_enabled"] = False
    return await _unifi("POST", "/rest/networkconf", json_body=payload)

@mcp.tool()
async def unifi_port_profiles():
    """List all UniFi switch port profiles."""
    return await _unifi("GET", "/rest/portconf")

@mcp.tool()
async def unifi_set_port_profile(device_mac: str, port_idx: int, port_profile_id: str):
    """Assign a port profile to a specific switch port.
    device_mac: switch MAC address
    port_idx: port number (1-based)
    port_profile_id: ID from unifi_port_profiles()
    """
    payload = {
        "port_overrides": [
            {"port_idx": port_idx, "portconf_id": port_profile_id}
        ]
    }
    return await _unifi("PUT", f"/rest/device/{device_mac}", json_body=payload)

@mcp.tool()
async def unifi_block_client(client_mac: str):
    """Block a client by MAC address in UniFi."""
    return await _unifi("POST", "/cmd/stamgr", json_body={"cmd": "block-sta", "mac": client_mac})

@mcp.tool()
async def unifi_unblock_client(client_mac: str):
    """Unblock a client by MAC address in UniFi."""
    return await _unifi("POST", "/cmd/stamgr", json_body={"cmd": "unblock-sta", "mac": client_mac})

@mcp.tool()
async def unifi_restart_device(device_mac: str):
    """Restart a UniFi device by MAC address."""
    return await _unifi("POST", "/cmd/devmgr", json_body={"cmd": "restart", "mac": device_mac})

@mcp.tool()
async def unifi_device_status(device_mac: str):
    """Get detailed status for a specific UniFi device."""
    result = await _unifi("GET", f"/stat/device/{device_mac}")
    return result


# ─── ASGI middleware + entrypoint ─────────────────────────────────────────────

class RewriteSpotToMcp:
    """Rewrite / and /spot[/...] -> /mcp[/...] for ChatGPT/Cloudflare MCP."""
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            path = scope.get("path", "")

            if path in ("", "/", "/spot"):
                scope["path"] = "/mcp"
                scope["raw_path"] = b"/mcp"
            elif path.startswith("/spot/"):
                new_path = "/mcp/" + path[len("/spot/"):]
                scope["path"] = new_path
                scope["raw_path"] = new_path.encode()

        await self.app(scope, receive, send)


if __name__ == "__main__":
    mcp_asgi = mcp.streamable_http_app()
    app = RewriteSpotToMcp(mcp_asgi)
    uvicorn.run(app, host="127.0.0.1", port=8000)
