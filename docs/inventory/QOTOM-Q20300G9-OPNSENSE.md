# Qotom Q20300G9 — Planned OPNsense Firewall

## Status

Planned / staging.

This unit is intended to become the new OPNsense firewall after installation, validation, and operator approval.

## Hardware

- Model: Qotom Q20300G9
- CPU: Intel Atom C3758R
- Memory: 16GB RAM
- Storage: 256GB SSD
- Network:
  - 4× SFP+ 10G
  - 5× 2.5G Intel I226-V

## Intended Role

- New primary OPNsense firewall
- Future network edge for Starfleet/Spot infrastructure

## Governance Boundary

This unit is not active production firewall authority yet.

Before production cutover:

- Backup current firewall configuration
- Export OPNsense config
- Confirm WAN/LAN/VLAN mappings
- Confirm management access path
- Confirm rollback path
- Validate DNS/DHCP/VPN/firewall rules
- Operator approval required before cutover

## Current State

- Hardware identified
- OPNsense setup pending / in progress
- Not yet production active
