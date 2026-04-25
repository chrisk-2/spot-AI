# Network DNS / Cloudflare Checkpoint

Date: 2026-04-25

## LAN DNS

Primary DNS:
- 192.168.60.10 = dns-core / AdGuard primary

Secondary DNS:
- 192.168.60.20 = starfleet-core / AdGuard secondary / UniFi

DHCP hands out:
- DNS 1: 192.168.60.10
- DNS 2: 192.168.60.20
- Domain: starfleet.local
- NTP: 192.168.60.20

Dynamic DNS in Kea:
- left blank intentionally

## Important LAN rewrites

- dns-core.starfleet.local -> 192.168.60.10
- starfleet-core.starfleet.local -> 192.168.60.20
- spot-core.starfleet.local -> 192.168.60.30
- spotapi.starfleet.local -> 192.168.60.30
- spotmcp.starfleet.local -> 192.168.60.30
- dashboard.starfleet.local -> 192.168.30.5

## Cloudflare tunnel routes

- mcp.starfleetcore.com -> http://localhost:8001
- api.starfleetcore.com -> http://localhost:8787

## ChatGPT MCP connector

Active URL:
- https://mcp.starfleetcore.com/spot/

Confirmed:
- MCP health OK
- LAN DNS resolution OK
- public DNS route OK

## Remote Spot UI

- spot.starfleetcore.com -> Cloudflare Tunnel -> http://localhost:8787
- / now serves read-only Spot Core Operator Dashboard
- no admin/write controls exposed
- mcp.starfleetcore.com remains isolated for ChatGPT MCP at http://localhost:8001

## Do not change yet

- firewall rules
- NAT
- VLAN policies
- DNS hijacking / forced DNS
- Cloudflare Access / Zero Trust
