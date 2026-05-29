# Module — Sandbox Executor Pilot

## Scope

First constrained live executor pilot.

Allowed mutation scope:

- /tmp/spot-sandbox-pilot/

Forbidden:

- service restart
- system config mutation
- firewall/DNS/DHCP/routing/SSH mutation
- production path writes
- worker self-apply

## Gates

- explicit operator approval via SPOT_SANDBOX_APPROVED=YES
- kill switch checked
- backup created
- rollback plan written
- action journal written
- rollback journal written
- validator confirms final state

## Governance Boundary

This module enables sandbox-live execution only.

It does not grant live infrastructure mutation authority.
