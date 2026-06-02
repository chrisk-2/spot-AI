# Module — Live Fleet Reachability Validation

## Scope

Add physical fleet reachability validation.

## Problem

`spot validate` can pass from Spot Core runtime inventory even when a worker is physically unreachable.

## Required checks

- hostname resolution
- ICMP reachability
- SSH reachability
- hostname matches expected worker
- ssh service active
- ollama service active for worker nodes

## Boundary

This module is read-only.

It does not:

- restart services
- change routing
- quarantine workers
- modify worker state
- enable execution authority
