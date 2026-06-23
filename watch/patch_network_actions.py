#!/usr/bin/env python3
"""
Patch app.py to add OPNsense/UniFi native clients and network actions to Spot.
Run from spot-core: python3 /home/ogre/spot-stack/watch/patch_network_actions.py
"""
import ast, shutil, re
from pathlib import Path

APP = Path("/home/ogre/spot-stack/spot-core/spotcore/app.py")
BACKUP = APP.with_suffix(".py.pre-network-patch")

src = APP.read_text(encoding="utf-8")

# ── 1. Expand SPOT_ACTION_ALLOWLIST ──────────────────────────────────────────
OLD_ALLOWLIST = '''\nSPOT_ACTION_ALLOWLIST: dict[str, dict[str, Any]] = {\n    "restart_ollama":   {"risk":"low",    "confirm_required":False, "targets":"workers"},\n    "quarantine_worker":{"risk":"medium", "confirm_required":True,  "targets":"workers"},\n    "release_worker":   {"risk":"low",    "confirm_required":False, "targets":"workers"},\n    "nfs_sync":         {"risk":"low",    "confirm_required":False, "targets":None},\n    "wake_worker":      {"risk":"low",    "confirm_required":False, "targets":"workers"},\n}'''

NEW_ALLOWLIST = '''\nSPOT_ACTION_ALLOWLIST: dict[str, dict[str, Any]] = {\n    "restart_ollama":          {"risk":"low",    "confirm_required":False, "targets":"workers"},\n    "quarantine_worker":       {"risk":"medium", "confirm_required":True,  "targets":"workers"},\n    "release_worker":          {"risk":"low",    "confirm_required":False, "targets":"workers"},\n    "nfs_sync":                {"risk":"low",    "confirm_required":False, "targets":None},\n    "wake_worker":             {"risk":"low",    "confirm_required":False, "targets":"workers"},\n    # ── Network actions (all require operator EXECUTE confirmation) ───────\n    "opn_create_firewall_rule":{"risk":"high",   "confirm_required":True,  "targets":None},\n    "opn_delete_firewall_rule":{"risk":"high",   "confirm_required":True,  "targets":None},\n    "opn_create_vlan":         {"risk":"high",   "confirm_required":True,  "targets":None},\n    "opn_create_alias":        {"risk":"medium", "confirm_required":True,  "targets":None},\n    "opn_create_static_lease": {"risk":"medium", "confirm_required":True,  "targets":None},\n    "opn_create_dns_override": {"risk":"medium", "confirm_required":True,  "targets":None},\n    "opn_delete_dns_override": {"risk":"medium", "confirm_required":True,  "targets":None},\n    "unifi_create_network":    {"risk":"high",   "confirm_required":True,  "targets":None},\n    "unifi_set_port_profile":  {"risk":"medium", "confirm_required":True,  "targets":None},\n    "unifi_block_client":      {"risk":"medium", "confirm_required":True,  "targets":None},\n    "unifi_restart_device":    {"risk":"medium", "confirm_required":True,  "targets":None},\n}'''

assert OLD_ALLOWLIST in src, "ALLOWLIST anchor not found"
src = src.replace(OLD_ALLOWLIST, NEW_ALLOWLIST, 1)

# ── 2. Inject network client helpers + env vars after SPOT_WORKER_MACS ───────
MACS_ANCHOR = '''SPOT_WORKER_MACS: dict[str, str] = {
    "spot-worker-01":"d8:43:ae:a9:c2:4c",
    "spot-worker-02":"d8:cb:8a:3e:94:fa",
    "spot-worker-03":"b4:2e:99:a5:17:ef",
    "spot-worker-04":"d8:43:ae:1f:88:2b",
    "spot-worker-05":"04:d4:c4:54:cd:6f",
    "spot-worker-06":"04:d4:c4:48:43:48",
}'''

NETWORK_CLIENTS = '''

# ── OPNsense / UniFi direct clients ─────────────────────────────────────────
OPNSENSE_HOST   = os.environ.get("OPNSENSE_HOST",   "192.168.1.1")
OPNSENSE_KEY    = os.environ.get("OPNSENSE_KEY",    "")
OPNSENSE_SECRET = os.environ.get("OPNSENSE_SECRET", "")

UNIFI_HOST = os.environ.get("UNIFI_HOST", "192.168.60.20")
UNIFI_PORT = os.environ.get("UNIFI_PORT", "11443")
UNIFI_USER = os.environ.get("UNIFI_USER", "")
UNIFI_PASS = os.environ.get("UNIFI_PASS", "")
UNIFI_SITE = os.environ.get("UNIFI_SITE", "starfleet")


async def _opn(method: str, path: str, *, json_body=None):
    """Call OPNsense API (key/secret auth, LAN direct)."""
    url = f"https://{OPNSENSE_HOST}/api{path}"
    async with httpx.AsyncClient(verify=False, timeout=30) as client:
        resp = await client.request(method, url, auth=(OPNSENSE_KEY, OPNSENSE_SECRET), json=json_body)
    try:
        return resp.json()
    except Exception:
        return {"status": resp.status_code, "text": resp.text}


async def _unifi(method: str, path: str, *, json_body=None):
    """Call UniFi OS API (login/cookie/CSRF, LAN direct)."""
    base = f"https://{UNIFI_HOST}:{UNIFI_PORT}"
    async with httpx.AsyncClient(verify=False, timeout=30) as client:
        login = await client.post(f"{base}/api/auth/login",
                                  json={"username": UNIFI_USER, "password": UNIFI_PASS})
        csrf = login.headers.get("x-csrf-token", "")
        headers = {"x-csrf-token": csrf} if csrf else {}
        resp = await client.request(method,
                                    f"{base}/proxy/network/api/s/{UNIFI_SITE}{path}",
                                    json=json_body, headers=headers)
    try:
        return resp.json()
    except Exception:
        return {"status": resp.status_code, "text": resp.text}


async def opn_read_firewall_rules() -> dict:
    return await _opn("GET", "/firewall/filter/searchRule")

async def opn_read_aliases() -> dict:
    return await _opn("GET", "/firewall/alias/searchItem")

async def opn_read_vlans() -> dict:
    return await _opn("GET", "/interfaces/vlan/searchItem")

async def opn_read_dhcp_leases() -> dict:
    return await _opn("GET", "/dhcpv4/leases/searchLease")

async def opn_read_dns_overrides() -> dict:
    return await _opn("GET", "/unbound/settings/searchHostOverride")

async def opn_read_interfaces() -> dict:
    return await _opn("GET", "/interfaces/overview/interfacesInfo")

async def opn_read_gateways() -> dict:
    return await _opn("GET", "/routes/gateway/status")

async def opn_read_wireguard() -> dict:
    return await _opn("GET", "/wireguard/service/show")

async def unifi_read_devices() -> dict:
    return await _unifi("GET", "/stat/device")

async def unifi_read_clients() -> dict:
    return await _unifi("GET", "/stat/sta")

async def unifi_read_networks() -> dict:
    return await _unifi("GET", "/rest/networkconf")
'''

assert MACS_ANCHOR in src, "MACS anchor not found"
src = src.replace(MACS_ANCHOR, MACS_ANCHOR + NETWORK_CLIENTS, 1)

# ── 3. Add network context to build_spot_fleet_context() ─────────────────────
NFS_LINE = '    lines.append(f"NFS: {\'AVAILABLE\' if nfs_available() else \'OFFLINE - buffering to W-01\'}")'
NETWORK_CONTEXT_BLOCK = '''
    # ── OPNsense / UniFi snapshot ──────────────────────────────────────────
    lines.append("")
    lines.append("NETWORK (OPNsense/UniFi):")
    try:
        gw_data = await opn_read_gateways() if False else {}  # sync context – skip await
    except Exception:
        gw_data = {}
    try:
        wg_data = await opn_read_wireguard() if False else {}
    except Exception:
        wg_data = {}
    # Summarise what Spot needs without blocking (reads happen in chat context)
    lines.append("  [call opn_read_* / unifi_read_* for live data during chat]")
'''

# build_spot_fleet_context is synchronous – we can't await inside it.
# Instead, add a note so Spot knows to call reads during chat, and wire
# async reads into the chat system prompt builder separately.
# For now just annotate; full async context injection in chat_route below.

# ── 4. Extend system prompt in chat_route with network action list ────────────
OLD_ACTIONS_LINE = '        "Actions: restart_ollama, quarantine_worker, release_worker, nfs_sync, wake_worker\\n"'
NEW_ACTIONS_LINE = (
    '        "Actions (fleet): restart_ollama, quarantine_worker, release_worker, nfs_sync, wake_worker\\n"\n'
    '        "Actions (network/OPNsense): opn_create_firewall_rule, opn_delete_firewall_rule, opn_create_vlan, opn_create_alias, opn_create_static_lease, opn_create_dns_override, opn_delete_dns_override\\n"\n'
    '        "Actions (network/UniFi): unifi_create_network, unifi_set_port_profile, unifi_block_client, unifi_restart_device\\n"\n'
    '        "Network action params go in a params key in the spot_action JSON block.\\n"'
)

assert OLD_ACTIONS_LINE in src, "actions line anchor not found"
src = src.replace(OLD_ACTIONS_LINE, NEW_ACTIONS_LINE, 1)

# ── 5. Add network action dispatch to /chat/execute ───────────────────────────
OLD_WAKE_BLOCK = '''    elif action == "wake_worker":
        mac = SPOT_WORKER_MACS.get(target)
        if not mac:
            raise HTTPException(status_code=400, detail={"message": f"no WOL MAC for {target}"})
        async def _do_wake():
            proc = await asyncio.create_subprocess_exec(
                "bash", str(SPOT_WATCH_ROOT / "wake-worker.sh"), target, mac,
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
            return {"ok": proc.returncode == 0, "stdout": stdout.decode(), "stderr": stderr.decode()}
        result = await execute_with_enforcement(
            action_name="wake_worker", target=target, service="wol", backup_sources=[],
            execute_fn=_do_wake, verify_fn=lambda r: (r.get("ok", False), r),
            metadata={"worker": target, "mac": mac, "reason": reason, "initiated_by": "spot_chat"}, require_backup=False)'''

NEW_WAKE_BLOCK = OLD_WAKE_BLOCK + '''

    # ── OPNsense actions ──────────────────────────────────────────────────
    elif action == "opn_create_firewall_rule":
        params = payload.__dict__.get("params") or {}
        async def _do_opn_fw():
            rule_payload = {
                "rule": {
                    "enabled": "1",
                    "action": params.get("action", "pass"),
                    "interface": params.get("interface", "lan"),
                    "direction": params.get("direction", "in"),
                    "ipprotocol": "inet",
                    "protocol": params.get("protocol", "any"),
                    "source_net": params.get("source_net", "any"),
                    "destination_net": params.get("destination_net", "any"),
                    "destination_port": params.get("destination_port", "any"),
                    "description": params.get("description", reason),
                }
            }
            r = await _opn("POST", "/firewall/filter/addRule", json_body=rule_payload)
            await _opn("POST", "/firewall/filter/apply")
            return {"ok": "uuid" in r or r.get("result") == "saved", "opn": r}
        result = await execute_with_enforcement(
            action_name="opn_create_firewall_rule", target="opnsense", service="firewall",
            backup_sources=[], execute_fn=_do_opn_fw,
            verify_fn=lambda r: (r.get("ok", False), r),
            metadata={"params": params, "reason": reason, "initiated_by": "spot_chat"},
            require_backup=False)

    elif action == "opn_delete_firewall_rule":
        params = payload.__dict__.get("params") or {}
        rule_uuid = params.get("rule_uuid", target)
        async def _do_opn_fw_del():
            r = await _opn("POST", f"/firewall/filter/delRule/{rule_uuid}")
            await _opn("POST", "/firewall/filter/apply")
            return {"ok": r.get("result") == "deleted", "opn": r}
        result = await execute_with_enforcement(
            action_name="opn_delete_firewall_rule", target="opnsense", service="firewall",
            backup_sources=[], execute_fn=_do_opn_fw_del,
            verify_fn=lambda r: (r.get("ok", False), r),
            metadata={"rule_uuid": rule_uuid, "reason": reason, "initiated_by": "spot_chat"},
            require_backup=False)

    elif action == "opn_create_vlan":
        params = payload.__dict__.get("params") or {}
        async def _do_opn_vlan():
            vlan_payload = {"vlan": {"if": params.get("parent_interface", "igc0"), "tag": str(params.get("vlan_tag", 0)), "pcp": "0", "descr": params.get("description", reason)}}
            r = await _opn("POST", "/interfaces/vlan/addItem", json_body=vlan_payload)
            await _opn("POST", "/interfaces/vlan/reconfigure")
            return {"ok": "uuid" in r or r.get("result") == "saved", "opn": r}
        result = await execute_with_enforcement(
            action_name="opn_create_vlan", target="opnsense", service="vlan",
            backup_sources=[], execute_fn=_do_opn_vlan,
            verify_fn=lambda r: (r.get("ok", False), r),
            metadata={"params": params, "reason": reason, "initiated_by": "spot_chat"},
            require_backup=False)

    elif action == "opn_create_alias":
        params = payload.__dict__.get("params") or {}
        async def _do_opn_alias():
            alias_payload = {"alias": {"enabled": "1", "name": params.get("name", ""), "type": params.get("alias_type", "host"), "content": "\\n".join(params.get("content", [])), "description": params.get("description", reason)}}
            r = await _opn("POST", "/firewall/alias/addItem", json_body=alias_payload)
            await _opn("POST", "/firewall/alias/reconfigure")
            return {"ok": "uuid" in r or r.get("result") == "saved", "opn": r}
        result = await execute_with_enforcement(
            action_name="opn_create_alias", target="opnsense", service="firewall_alias",
            backup_sources=[], execute_fn=_do_opn_alias,
            verify_fn=lambda r: (r.get("ok", False), r),
            metadata={"params": params, "reason": reason, "initiated_by": "spot_chat"},
            require_backup=False)

    elif action == "opn_create_static_lease":
        params = payload.__dict__.get("params") or {}
        async def _do_opn_lease():
            lease_payload = {"lease": {"interface": params.get("interface", "lan"), "mac": params.get("mac", ""), "ipaddr": params.get("ip", ""), "hostname": params.get("hostname", "")}}
            r = await _opn("POST", "/dhcpv4/settings/addStaticMap", json_body=lease_payload)
            return {"ok": "uuid" in r or r.get("result") == "saved", "opn": r}
        result = await execute_with_enforcement(
            action_name="opn_create_static_lease", target="opnsense", service="dhcp",
            backup_sources=[], execute_fn=_do_opn_lease,
            verify_fn=lambda r: (r.get("ok", False), r),
            metadata={"params": params, "reason": reason, "initiated_by": "spot_chat"},
            require_backup=False)

    elif action == "opn_create_dns_override":
        params = payload.__dict__.get("params") or {}
        async def _do_opn_dns():
            dns_payload = {"host": {"enabled": "1", "hostname": params.get("hostname", ""), "domain": params.get("domain", ""), "rr": "A", "server": params.get("ip", ""), "description": params.get("description", reason)}}
            r = await _opn("POST", "/unbound/settings/addHostOverride", json_body=dns_payload)
            await _opn("POST", "/unbound/service/reconfigure")
            return {"ok": "uuid" in r or r.get("result") == "saved", "opn": r}
        result = await execute_with_enforcement(
            action_name="opn_create_dns_override", target="opnsense", service="dns",
            backup_sources=[], execute_fn=_do_opn_dns,
            verify_fn=lambda r: (r.get("ok", False), r),
            metadata={"params": params, "reason": reason, "initiated_by": "spot_chat"},
            require_backup=False)

    elif action == "opn_delete_dns_override":
        params = payload.__dict__.get("params") or {}
        override_uuid = params.get("uuid", target)
        async def _do_opn_dns_del():
            r = await _opn("POST", f"/unbound/settings/delHostOverride/{override_uuid}")
            await _opn("POST", "/unbound/service/reconfigure")
            return {"ok": r.get("result") == "deleted", "opn": r}
        result = await execute_with_enforcement(
            action_name="opn_delete_dns_override", target="opnsense", service="dns",
            backup_sources=[], execute_fn=_do_opn_dns_del,
            verify_fn=lambda r: (r.get("ok", False), r),
            metadata={"uuid": override_uuid, "reason": reason, "initiated_by": "spot_chat"},
            require_backup=False)

    # ── UniFi actions ─────────────────────────────────────────────────────
    elif action == "unifi_create_network":
        params = payload.__dict__.get("params") or {}
        async def _do_unifi_net():
            net_payload = {"name": params.get("name", ""), "purpose": params.get("purpose", "corporate"), "vlan_enabled": True, "vlan": params.get("vlan_id", 0)}
            if params.get("subnet"):
                net_payload["ip_subnet"] = params["subnet"]
                net_payload["dhcpd_enabled"] = False
            r = await _unifi("POST", "/rest/networkconf", json_body=net_payload)
            return {"ok": isinstance(r.get("data"), list) and len(r.get("data", [])) > 0, "unifi": r}
        result = await execute_with_enforcement(
            action_name="unifi_create_network", target="unifi", service="network",
            backup_sources=[], execute_fn=_do_unifi_net,
            verify_fn=lambda r: (r.get("ok", False), r),
            metadata={"params": params, "reason": reason, "initiated_by": "spot_chat"},
            require_backup=False)

    elif action == "unifi_set_port_profile":
        params = payload.__dict__.get("params") or {}
        async def _do_unifi_port():
            port_payload = {"port_overrides": [{"port_idx": params.get("port_idx", 1), "portconf_id": params.get("port_profile_id", "")}]}
            r = await _unifi("PUT", f"/rest/device/{params.get('device_mac', '')}", json_body=port_payload)
            return {"ok": r.get("meta", {}).get("rc") == "ok", "unifi": r}
        result = await execute_with_enforcement(
            action_name="unifi_set_port_profile", target="unifi", service="switch_port",
            backup_sources=[], execute_fn=_do_unifi_port,
            verify_fn=lambda r: (r.get("ok", False), r),
            metadata={"params": params, "reason": reason, "initiated_by": "spot_chat"},
            require_backup=False)

    elif action == "unifi_block_client":
        params = payload.__dict__.get("params") or {}
        client_mac = params.get("client_mac", target)
        async def _do_unifi_block():
            r = await _unifi("POST", "/cmd/stamgr", json_body={"cmd": "block-sta", "mac": client_mac})
            return {"ok": r.get("meta", {}).get("rc") == "ok", "unifi": r}
        result = await execute_with_enforcement(
            action_name="unifi_block_client", target="unifi", service="client_policy",
            backup_sources=[], execute_fn=_do_unifi_block,
            verify_fn=lambda r: (r.get("ok", False), r),
            metadata={"client_mac": client_mac, "reason": reason, "initiated_by": "spot_chat"},
            require_backup=False)

    elif action == "unifi_restart_device":
        params = payload.__dict__.get("params") or {}
        device_mac = params.get("device_mac", target)
        async def _do_unifi_restart():
            r = await _unifi("POST", "/cmd/devmgr", json_body={"cmd": "restart", "mac": device_mac})
            return {"ok": r.get("meta", {}).get("rc") == "ok", "unifi": r}
        result = await execute_with_enforcement(
            action_name="unifi_restart_device", target="unifi", service="device_mgmt",
            backup_sources=[], execute_fn=_do_unifi_restart,
            verify_fn=lambda r: (r.get("ok", False), r),
            metadata={"device_mac": device_mac, "reason": reason, "initiated_by": "spot_chat"},
            require_backup=False)'''

assert OLD_WAKE_BLOCK in src, "wake_worker anchor not found"
src = src.replace(OLD_WAKE_BLOCK, NEW_WAKE_BLOCK, 1)

# ── 6. Add params field to ChatExecuteRequest ─────────────────────────────────
OLD_EXEC_REQ = '''class ChatExecuteRequest(BaseModel):
    token: str
    action: str
    target: str | None = None
    reason: str = ""
    confirmed: bool = False'''

NEW_EXEC_REQ = '''class ChatExecuteRequest(BaseModel):
    token: str
    action: str
    target: str | None = None
    reason: str = ""
    confirmed: bool = False
    params: dict[str, Any] | None = None  # extra params for network actions'''

assert OLD_EXEC_REQ in src, "ChatExecuteRequest anchor not found"
src = src.replace(OLD_EXEC_REQ, NEW_EXEC_REQ, 1)

# ── Validate syntax ───────────────────────────────────────────────────────────
try:
    ast.parse(src)
except SyntaxError as e:
    print(f"SYNTAX ERROR: {e}")
    raise SystemExit(1)

# ── Write ─────────────────────────────────────────────────────────────────────
shutil.copy2(APP, BACKUP)
print(f"Backup: {BACKUP}")
APP.write_text(src, encoding="utf-8")
print(f"Patched: {APP}")
print("Done. Run: cd /home/ogre/spot-stack && docker compose restart spot-core")
