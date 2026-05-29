# Module — Lease Receipt Reconciliation Auditing

## Scope

This module adds read-only lease/receipt reconciliation auditing.

It cross-checks modeled lease, receipt, rollback, lifecycle, drift, and reconciliation artifacts without modifying runtime state.

## Added

- watch/governance/lease-receipt-reconciliation-audit.py
- watch/governance/lease-receipt-reconciliation-validate.py
- watch/governance/lease-receipt-reconciliation-history.py

## Operator Commands

- lease-receipt-reconciliation
- lease-receipt-reconciliation-validate
- lease-receipt-reconciliation-history

## Outputs

- watch/state/lease-receipt-reconciliation-audit.json
- watch/state/lease-receipt-reconciliation-history.jsonl

## Audit Classifications

- NONE
- LEASE_MISSING
- RECEIPT_MISSING
- LEASE_RECEIPT_MISMATCH
- CHAIN_BREAK
- ROLLBACK_BINDING_MISSING
- RECONCILIATION_MISMATCH

## Governance Invariants

- mode: read_only
- advisory_only: true
- execution_allowed: false
- mutation_authority: false
- live_executor_enabled: false

## Safety Boundary

This module does not:

- execute commands
- restart services
- create leases
- modify leases
- create receipts
- modify receipts
- modify rollback bindings
- mutate reconciliation journals
- grant executor authority
