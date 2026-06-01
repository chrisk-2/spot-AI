# Module F — Node Loss Simulation

## Scope

Define read-only node-loss simulation artifacts.

## Purpose

Prove expected routing and operator response behavior when a worker is unavailable, without shutting down or modifying any worker.

## Boundaries

This module does not:

- stop workers
- quarantine workers
- change eligibility
- change routing
- restart services
- mutate fleet state

## Required simulation fields

- target_worker
- locked_role
- expected_loss_mode
- expected_operator_action
- expected_validation
- recovery_reference
