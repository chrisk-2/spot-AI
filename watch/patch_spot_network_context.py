#!/usr/bin/env python3
"""Inject live OPNsense/UniFi summary into Spot's chat system prompt."""
import ast, shutil
from pathlib import Path

APP = Path("/home/ogre/spot-stack/spot-core/spotcore/app.py")
BACKUP = APP.with_suffix(".py.pre-network-context")
src = APP.read_text(encoding="utf-8")

OLD = '''    fleet_context = build_spot_fleet_context()
    identity = build_spot_identity()
    history = load_chat_history()

    system_prompt = ('''

NEW = '''    fleet_context = build_spot_fleet_context()
    identity = build_spot_identity()
    history = load_chat_history()

    # Live network snapshot for Spot
    network_context = ""
    try:
        gw = await opn_read_gateways()
        items = gw.get("items") or []
        gw_lines = [f"  {g.get('name','?')}: {g.get('status','?')} loss={g.get('loss','?')} rtt={g.get('delay','?')}" for g in items[:6]]
        wg = await opn_read_wireguard()
        peers = (wg.get("rows") or wg.get("items") or [])
        wg_lines = [f"  {p.get('name','?')}: {'up' if p.get('status') == 'up' else 'down'} endpoint={p.get('endpoint','?')}" for p in peers[:6]]
        unifi_devs = await unifi_read_devices()
        devs = (unifi_devs.get("data") or [])
        dev_lines = [f"  {d.get('name') or d.get('mac','?')}: {d.get('state',0)} uptime={d.get('uptime','?')}" for d in devs[:8]]
        network_context = (
            "\\nNETWORK STATE:\\n"
            "OPNsense Gateways:\\n" + ("\\n".join(gw_lines) or "  none") + "\\n"
            "WireGuard Peers:\\n" + ("\\n".join(wg_lines) or "  none") + "\\n"
            "UniFi Devices:\\n" + ("\\n".join(dev_lines) or "  none") + "\\n"
            "Use opn_read_firewall_rules/opn_read_aliases/opn_read_dhcp_leases/opn_read_dns_overrides/unifi_read_clients/unifi_read_networks for deeper data."
        )
    except Exception as _net_exc:
        network_context = f"\\nNETWORK STATE: unavailable ({_net_exc})"

    system_prompt = ('''

OLD_FLEET = '        \"LIVE FLEET STATE:\\n\"\n        + fleet_context\n    )'
NEW_FLEET = '        \"LIVE FLEET STATE:\\n\"\n        + fleet_context\n        + network_context\n    )'

assert OLD in src, "chat_route anchor not found"
assert OLD_FLEET in src, "fleet_context anchor not found"
src = src.replace(OLD, NEW, 1)
src = src.replace(OLD_FLEET, NEW_FLEET, 1)

ast.parse(src)
shutil.copy2(APP, BACKUP)
APP.write_text(src, encoding="utf-8")
print("Done")
