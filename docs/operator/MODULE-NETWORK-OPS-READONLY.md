# Module — Network Ops Readonly

## Scope

This module adds read-only network truth collection for Spot operator workflows.

## Added

- watch/network/network-truth-snapshot.py
- watch/network/network-truth-validate.py
- operator command: network-truth
- operator command: network-validate

## Data Collected

- Spot Core health
- fleet ping state
- routing map
- routing audit summary
- fleet status file
- local routes
- local interface addresses
- local DNS resolver state
- local listening ports

## Safety Boundary

This module is read-only.

It does not:
- modify firewall rules
- modify DNS
- modify DHCP
- modify routes
- restart services
- write network configuration
- change OPNsense
- change VLANs

## Policy

Network remediation remains future work.

This module only creates the diagnostic truth surface needed before any controlled network remediation design.
