# Runtime Queue Lease Model

Scope: fixture/simulation only.

Lease rules:
- lease owner must be spot-core
- workers cannot claim execution leases
- expired leases cannot execute
- duplicate leases are blocked
- stale leases are recoverable
- terminal candidates cannot be leased again

Terminal states:
- completed
- denied
- expired

Forbidden:
- production target execution
- network/firewall/DNS/DHCP/routing mutation
- worker self-apply
- Codex mutation
- OpenAI mutation
