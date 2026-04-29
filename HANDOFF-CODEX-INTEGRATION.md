# Spot / Codex System Integration Plan

Codex is a constrained engineering assistant for Starfleet OS.

Core rule:

Codex proposes. Spot Core applies.

Codex may read, plan, generate patches, and request validation. Codex must not receive direct shell, root, Docker socket, firewall, DNS, DHCP, VLAN, routing, or unrestricted filesystem mutation authority.

Required workflow:

read -> propose -> validate -> approve -> apply through Spot Core -> verify -> log/update handoff

High-risk network/security changes remain blocked unless implemented through narrow Spot Core endpoints with backup, verification, logging, and explicit approval.
