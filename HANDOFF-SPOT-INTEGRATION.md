# Spot Integration Plan

Spot Core is the Starfleet OS control plane. Everything else is a client.

Core rule:

Spot Core holds the keys. Everything else asks permission.

Spot integration must preserve:

- no backup, no change
- classify before mutation
- backup-first writes
- verification after mutation
- action logging
- no high-risk firewall/DNS/DHCP/VLAN/routing/OPNsense mutation without narrow approved endpoints

Current integration direction:

1. stabilize Spot Core
2. build operator read/validation surface
3. route controlled file mutation through Spot Core
4. integrate Codex as a proposal-first client
5. start network operations read-only
6. add proposal-only network planning
7. add narrow high-risk mutation endpoints only after read-only workflows prove stable
