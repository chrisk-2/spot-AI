# Module — UI Operator Integration Cleanup

## Scope

This module normalizes UI-facing operator status export and validation.

## Added

- watch/ui/ui-operator-status-export.py
- watch/ui/ui-operator-status-validate.py
- operator command: ui-status
- operator command: ui-status-validate

## Exported Validation Surfaces

- fleet validation
- network validation
- runtime validation
- capability validation

## Output

Generated file:

    starfleet-ui/public/operator-status.json

## Safety Boundary

This module is read-only.

It does not:
- authorize execution
- modify runtime state
- restart services
- mutate routing
- mutate governance
- mutate worker ownership

## Policy

UI visibility remains informational only.
Mutation authority remains false.
Spot Core remains sole executor.
